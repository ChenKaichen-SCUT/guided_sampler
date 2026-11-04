# Use the modified Z3 built by ../scripts/build.sh.
.DEFAULT_GOAL := all

CXX ?= g++
Z3_PREFIX ?= $(abspath ../venv)
CPPFLAGS += -I$(Z3_PREFIX)/include
# Preserve the original artifact's HighDiv optimization level.
CXXFLAGS ?= -g -O0 -Wall -std=c++20
LDFLAGS += -L$(Z3_PREFIX)/lib -Wl,-rpath,$(Z3_PREFIX)/lib
LDLIBS += -lz3

SOURCES := $(wildcard src/main/*.cpp src/sampler/*.cpp)
OBJECTS := $(patsubst src/%.cpp,build/%.o,$(SOURCES))
TARGET := highdiv

.PHONY: all clean
all: $(TARGET)

$(TARGET): $(OBJECTS) $(Z3_PREFIX)/lib/libz3.so
	$(CXX) $(OBJECTS) $(LDFLAGS) $(LDLIBS) -o $@

build/%.o: src/%.cpp $(Z3_PREFIX)/include/z3++.h
	@mkdir -p $(dir $@)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -MMD -MP -c $< -o $@

$(Z3_PREFIX)/include/z3++.h $(Z3_PREFIX)/lib/libz3.so:
	@echo "Build the bundled Z3 first: bash ../scripts/build.sh" >&2
	@exit 1

clean:
	rm -rf build $(TARGET)

-include $(OBJECTS:.o=.d)
