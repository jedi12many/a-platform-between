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

.PHONY: all test test-6502 test-python test-vm test-term test-receipts test-combat c64 test-c64 demo play crosscheck registry check-registry check-content clean

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

# The game on the Commodore 64 (docs/c64.md): the main program plus three overlays,
# loaded from disk when the VM asks (LOAD, PASS and BATTLE), on cc65's overlay memory
# map (fe/c64/apb.cfg). The linker fails the build if anything doesn't fit.
C64_DEFS   := -DAPB_OVERLAYS -DAPB_VM_DEPOT_MAX=2048 -g
C64_MAIN   := fe/c64/c64.c fe/c64/split.s vm/vm.c client/view.c core/src/rng.c core/src/names.c \
              core/src/rules.c core/src/registry.c core/src/translate.c core/src/echo.c
C64_PASS   := client/desk.c core/src/passport.c client/receipt_view.c
C64_BATTLE := core/src/battle.c core/src/combat.c client/battle_view.c

build/c64/apb.prg: fe/c64/apb.cfg $(C64_MAIN) $(C64_PASS) $(C64_BATTLE) $(CORE_HDR) $(VM_HDR) \
                   client/apb_view.h | build
	@mkdir -p build/c64/obj
	@for f in $(C64_MAIN); do \
	    $(CL65) -t c64 -O $(INC) $(C64_DEFS) -c -o build/c64/obj/$$(basename $${f%.*}).o $$f || exit 1; done
	@for f in $(C64_PASS); do $(CL65) -t c64 -O $(INC) $(C64_DEFS) --code-name OVERLAY2 \
	    --rodata-name OVL2DATA -c -o build/c64/obj/$$(basename $$f .c).o $$f || exit 1; done
	@for f in $(C64_BATTLE); do $(CL65) -t c64 -O $(INC) $(C64_DEFS) --code-name OVERLAY3 \
	    --rodata-name OVL3DATA -c -o build/c64/obj/$$(basename $$f .c).o $$f || exit 1; done
	$(CL65) -t c64 -g -C fe/c64/apb.cfg -m build/c64/apb.map -Wl --dbgfile,build/c64/apb.dbg -o $@ \
	    $(addprefix build/c64/obj/,$(addsuffix .o,$(notdir $(basename $(C64_MAIN) $(C64_PASS) $(C64_BATTLE))))) c64.lib

# The Fare on a 1541 disk: LOAD"APB",8 and RUN. Its pictures (pic00, pic01, ...) come
# from the PNGs in its pictures/ folder (tools/c64pic.py, which needs Pillow).
FARE_PICS := $(wildcard content/s1/00-the-fare/pictures/*.png)

build/the-fare.d64: build/c64/apb.prg content/s1/00-the-fare/the-fare.qs tools/d64.py tools/c64pic.py $(FARE_PICS)
	@mkdir -p build/c64/fare build/c64/fare-pics
	python3 tools/qsc/qsc.py build content/s1/00-the-fare/the-fare.qs -o build/c64/the-fare.apd --split build/c64/fare
	python3 tools/c64pic.py disk build/c64/fare/DEPOT content/s1/00-the-fare/pictures build/c64/fare-pics
	python3 tools/d64.py write $@ "the fare" s1 build/c64/apb.prg=apb build/c64/apb.prg.1=ovl1 \
	    build/c64/apb.prg.2=ovl2 build/c64/apb.prg.3=ovl3 \
	    $$(for f in build/c64/fare/*; do printf '%s=%s,s ' $$f $$(basename $$f); done) \
	    $$(for f in build/c64/fare-pics/*; do printf '%s=%s ' $$f $$(basename $$f); done)

# The C64 game played without a C64: the real program, from the .d64, on a 6502 emulator
# (py65) with the KERNAL answered in Python (tests/c64/run_c64.py). The overlays must
# never reach into each other; The Fare's edge route must match its reviewed transcript
# and give the same Travel Stamp as the terminal; a fight, a save to disk and a resume
# after switching off must match theirs; and nothing may pass 40 columns.
test-c64: build/the-fare.d64 build/apb build/the-fare.apd
	python3 fe/c64/check_overlays.py build/c64/apb.dbg
	python3 tests/c64/run_c64.py build/the-fare.d64 build/c64/apb.dbg tests/c64/fare-edge.choices > build/c64-fare-edge.txt
	diff tests/c64/fare-edge.expected build/c64-fare-edge.txt
	./build/apb --choices tests/term/fare-edge.choices build/the-fare.apd | grep -A2 "^  [0-9A-Z]\{20\}$$" > build/term-stamp.txt
	grep -A2 "^  [0-9A-Z]\{20\}$$" build/c64-fare-edge.txt | grep -v "(press a key)" | diff build/term-stamp.txt -
	python3 tests/c64/run_c64.py build/the-fare.d64 build/c64/apb.dbg tests/c64/fare-fight.choices \
	    --then tests/c64/fare-resume.choices > build/c64-fare-fight.txt
	diff tests/c64/fare-fight.expected build/c64-fare-fight.txt
	@awk 'length > 40 { print FILENAME ": line over 40 columns: " $$0; bad = 1 } END { exit bad }' build/c64-fare-edge.txt build/c64-fare-fight.txt
	@echo "c64: no overlay reaches into another; transcripts match; same Travel Stamp as the terminal"

c64: build/demo.prg build/the-fare.d64
	@echo "C64 demo: build/demo.prg ($$(wc -c < build/demo.prg) bytes)"
	@echo "C64 game: build/the-fare.d64 (program $$(wc -c < build/c64/apb.prg) bytes;" \
	      "overlays $$(wc -c < build/c64/apb.prg.1), $$(wc -c < build/c64/apb.prg.2)," \
	      "$$(wc -c < build/c64/apb.prg.3))"

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
# Shared by every front end: the status line, checks and the battle screen.
VIEW_SRC := client/view.c client/battle_view.c client/receipt_view.c

build/apb: fe/term/term.c $(VIEW_SRC) client/apb_view.h $(VM_SRC) $(VM_HDR) $(CORE_SRC) $(CORE_HDR) | build
	$(CC) $(CFLAGS) $(WARN) $(INC) -o $@ fe/term/term.c $(VIEW_SRC) $(VM_SRC) $(CORE_SRC)

build/the-fare.apd: content/s1/00-the-fare/the-fare.qs | build
	python3 tools/qsc/qsc.py build $< -o $@

build/skirmish.apd: tests/term/skirmish.qs | build
	python3 tools/qsc/qsc.py build $< -o $@

play: build/apb build/the-fare.apd
	./build/apb build/the-fare.apd

# A recorded terminal playthrough must match its reviewed transcript. It boards with a
# Boarding Pass (seed 1985) from tools/passport/boarding.py issue "<Kestrel's Passport>"
# 0 1985 1985, typed loosely the way a player might. The skirmish is a recorded fight on
# the battle screen (seed 3, no pass): the map, the roster, both menus, a "Back", a guard
# and its free attack, a wait, and quick.
test-term: build/apb build/the-fare.apd build/skirmish.apd
	./build/apb --choices tests/term/fare-edge.choices build/the-fare.apd > build/term-fare-edge.txt
	diff tests/term/fare-edge.expected build/term-fare-edge.txt
	./build/apb --seed 3 --choices tests/term/skirmish.choices build/skirmish.apd > build/term-skirmish.txt
	diff tests/term/skirmish.expected build/term-skirmish.txt
	@awk 'length > 40 { print FILENAME ": line over 40 columns: " $$0; bad = 1 } END { exit bad }' build/term-fare-edge.txt build/term-skirmish.txt
	@echo "terminal: transcripts match, nothing over 40 columns"
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
