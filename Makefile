CC      ?= cc
CFLAGS  ?= -O2
WARN    := -std=c99 -pedantic -Wall -Wextra -Werror -Wdeclaration-after-statement
INC     := -Icore/include -Icore/src -Ihal -Ivm -Iclient
CL65    ?= cl65
SIM65   ?= sim65

CORE_SRC := core/src/rng.c core/src/names.c core/src/rules.c core/src/registry.c \
            core/src/translate.c core/src/echo.c core/src/passport.c core/src/combat.c
# Applying receipts happens at the Waystation, not in clients: kept out of CORE_SRC so
# cc65 doesn't link it into C64 programs that never call it.
APPLY_SRC := core/src/receipt.c
# The battle engine: about 10 KB of 6502 code, so only linked where it's used until it's
# made smaller (docs/engine-plan.md, Risks).
BATTLE_SRC := core/src/battle.c
CORE_HDR := core/include/apb.h core/include/apb_battle.h core/include/apb_registry.h core/src/names.h hal/apb_hal.h
VM_SRC   := vm/vm.c client/desk.c core/src/battle.c
VM_HDR   := vm/apb_vm.h client/apb_desk.h core/include/apb_battle.h

.PHONY: all test test-6502 test-python test-vm test-term test-receipts test-combat c64 demo play crosscheck registry check-registry check-content clean

all: test

build:
	mkdir -p build

build/test_core: tests/test_core.c $(CORE_SRC) $(CORE_HDR) | build
	$(CC) $(CFLAGS) $(WARN) $(INC) -o $@ tests/test_core.c $(CORE_SRC)

build/demo: demo/demo.c $(CORE_SRC) $(CORE_HDR) | build
	$(CC) $(CFLAGS) $(WARN) $(INC) -o $@ demo/demo.c $(CORE_SRC)

test: build/test_core
	./build/test_core

demo: build/demo
	./build/demo

# The same tests on a simulated 6502. Results must match the native run.
build/test_core.sim: tests/test_core.c $(CORE_SRC) $(CORE_HDR) | build
	$(CL65) -t sim6502 -O $(INC) -o $@ tests/test_core.c $(CORE_SRC)

test-6502: build/test_core.sim
	$(SIM65) build/test_core.sim

# Commodore 64 demo program: load "demo.prg" in VICE or on real hardware.
build/demo.prg: demo/demo.c $(CORE_SRC) $(CORE_HDR) | build
	$(CL65) -t c64 -O $(INC) -o $@ demo/demo.c $(CORE_SRC)

c64: build/demo.prg
	@echo "C64 demo: build/demo.prg ($$(wc -c < build/demo.prg) bytes)"

clean:
	rm -rf build
	rm -f core/src/*.o tests/*.o demo/*.o

# Run the demo on the 6502 simulator and require byte-identical output to the
# native build: same dice, same Translation, same Passport.
build/demo.sim: demo/demo.c $(CORE_SRC) $(CORE_HDR) | build
	$(CL65) -t sim6502 -O $(INC) -o $@ demo/demo.c $(CORE_SRC)

crosscheck: build/demo build/demo.sim
	./build/demo > build/demo.native.txt
	$(SIM65) build/demo.sim > build/demo.6502.txt
	diff build/demo.native.txt build/demo.6502.txt
	@echo "crosscheck: native and 6502 output identical"

# The Python Passport reference must read what the C engine writes.
test-python: build/demo
	./build/demo > build/demo.native.txt
	python3 tools/passport/check_against_demo.py build/demo.native.txt
	python3 tools/registry/test_registry.py
	python3 tools/qsc/test_qsc.py
	python3 tools/qsc/test_build.py

# Regenerate the C registry from registry/*.txt after editing them.
registry:
	python3 tools/registry/gen.py

# The committed C registry must match registry/*.txt.
check-registry: | build
	python3 tools/registry/gen.py build/registry
	diff core/include/apb_registry.h build/registry/apb_registry.h
	diff core/src/registry.c build/registry/registry.c
	@echo "registry: generated code matches registry/*.txt"

# Every Departure in content/ must compile to an image the verifier accepts.
check-content: | build
	@mkdir -p build/content
	@for f in $$(find content -name '*.qs' | sort); do \
		python3 tools/qsc/qsc.py build $$f -o build/content/$$(basename $$f .qs).apd || exit 1; \
	done

# The Story VM test harness, native and for sim65.
build/harness: tests/vm/harness.c $(VM_SRC) $(VM_HDR) $(CORE_SRC) $(CORE_HDR) | build
	$(CC) $(CFLAGS) $(WARN) $(INC) -o $@ tests/vm/harness.c $(VM_SRC) $(CORE_SRC)

# On the 6502 the harness uses a 4 KB car and a 2 KB depot buffer so that the VM, the
# battle engine and stdio fit the simulator's 64 KB (The Fare's biggest car is 3.3 KB; a
# car too big is refused at load, so a test fails loudly). Fitting the real C64 is
# milestone E4's memory work.
build/harness.sim: tests/vm/harness.c $(VM_SRC) $(VM_HDR) $(CORE_SRC) $(CORE_HDR) | build
	$(CL65) -t sim6502 -O -DAPB_VM_CAR_MAX=4096 -DAPB_VM_DEPOT_MAX=2048 $(INC) -o $@ tests/vm/harness.c $(VM_SRC) $(CORE_SRC)

# The same harness with AddressSanitizer and UndefinedBehaviorSanitizer, for damage tests.
build/harness.asan: tests/vm/harness.c $(VM_SRC) $(VM_HDR) $(CORE_SRC) $(CORE_HDR) | build
	$(CC) -O1 -g -fsanitize=address,undefined -fno-sanitize-recover=undefined $(WARN) $(INC) \
		-o $@ tests/vm/harness.c $(VM_SRC) $(CORE_SRC)

# The same harness, listing every instruction it runs: which code the playthroughs cover.
build/harness.cov: tests/vm/harness.c $(VM_SRC) $(VM_HDR) $(CORE_SRC) $(CORE_HDR) | build
	$(CC) $(CFLAGS) $(WARN) -DAPB_VM_TRACE $(INC) -o $@ tests/vm/harness.c $(VM_SRC) $(CORE_SRC)

# Story VM: playthroughs (native == expected, 6502 == native), coverage, damaged images.
test-vm: build/harness build/harness.sim build/harness.asan build/harness.cov
	python3 tests/vm/run_tests.py

# The terminal front end: `make play` compiles The Fare and plays it.
build/apb: fe/term/term.c $(VM_SRC) $(VM_HDR) $(CORE_SRC) $(CORE_HDR) | build
	$(CC) $(CFLAGS) $(WARN) $(INC) -o $@ fe/term/term.c $(VM_SRC) $(CORE_SRC)

build/the-fare.apd: content/s1/00-the-fare/the-fare.qs | build
	python3 tools/qsc/qsc.py build $< -o $@

play: build/apb build/the-fare.apd
	./build/apb build/the-fare.apd

# A recorded terminal playthrough must match its reviewed transcript. It boards with a
# Boarding Pass (seed 1985) from tools/passport/boarding.py issue "<Kestrel's Passport>"
# 0 1985 1985, typed loosely the way a player might.
test-term: build/apb build/the-fare.apd
	./build/apb --choices tests/term/fare-edge.choices build/the-fare.apd > build/term-fare-edge.txt
	diff tests/term/fare-edge.expected build/term-fare-edge.txt
	@awk 'length > 40 { print "line over 40 columns: " $$0; bad = 1 } END { exit bad }' build/term-fare-edge.txt
	@echo "terminal: transcript matches, nothing over 40 columns"
	python3 tests/term/check_roundtrip.py

# Applying receipts: the C core must agree with the Python reference, natively and on
# the 6502.
build/apply: tests/receipts/apply.c $(APPLY_SRC) $(CORE_SRC) $(CORE_HDR) | build
	$(CC) $(CFLAGS) $(WARN) $(INC) -o $@ tests/receipts/apply.c $(APPLY_SRC) $(CORE_SRC)

build/apply.sim: tests/receipts/apply.c $(APPLY_SRC) $(CORE_SRC) $(CORE_HDR) | build
	$(CL65) -t sim6502 -O $(INC) -o $@ tests/receipts/apply.c $(APPLY_SRC) $(CORE_SRC)

test-receipts: build/apply build/apply.sim
	python3 tests/receipts/check_apply.py

# Combat rules: the C core must agree with the Python reference, natively and on the 6502.
build/attack: tests/combat/attack.c $(CORE_SRC) $(CORE_HDR) | build
	$(CC) $(CFLAGS) $(WARN) $(INC) -o $@ tests/combat/attack.c $(CORE_SRC)

build/attack.sim: tests/combat/attack.c $(CORE_SRC) $(CORE_HDR) | build
	$(CL65) -t sim6502 -O $(INC) -o $@ tests/combat/attack.c $(CORE_SRC)

test-combat: build/attack build/attack.sim build/battle build/battle.sim build/battle.asan
	python3 tests/combat/check_combat.py
	python3 tests/battle/run_battles.py

# Battles: scenarios played natively and on the 6502, with the same log.
build/battle: tests/battle/battle.c $(BATTLE_SRC) $(CORE_SRC) $(CORE_HDR) | build
	$(CC) $(CFLAGS) $(WARN) $(INC) -o $@ tests/battle/battle.c $(BATTLE_SRC) $(CORE_SRC)

build/battle.sim: tests/battle/battle.c $(BATTLE_SRC) $(CORE_SRC) $(CORE_HDR) | build
	$(CL65) -t sim6502 -O $(INC) -o $@ tests/battle/battle.c $(BATTLE_SRC) $(CORE_SRC)

build/battle.asan: tests/battle/battle.c $(BATTLE_SRC) $(CORE_SRC) $(CORE_HDR) | build
	$(CC) -O1 -g -fsanitize=address,undefined -fno-sanitize-recover=undefined $(WARN) $(INC) \
		-o $@ tests/battle/battle.c $(BATTLE_SRC) $(CORE_SRC)
