CC      ?= cc
CFLAGS  ?= -O2
WARN    := -std=c99 -pedantic -Wall -Wextra -Werror -Wdeclaration-after-statement
INC     := -Icore/include -Icore/src -Ihal
CL65    ?= cl65
SIM65   ?= sim65

CORE_SRC := core/src/rng.c core/src/names.c core/src/rules.c \
            core/src/translate.c core/src/echo.c core/src/passport.c
CORE_HDR := core/include/apb.h core/include/apb_registry.h core/src/names.h hal/apb_hal.h

.PHONY: all test test-6502 test-python c64 demo crosscheck clean

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
