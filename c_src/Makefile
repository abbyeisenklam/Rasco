# Makefile for creating a shared library (DLL) for use with Python

CC = gcc
CFLAGS = -Wall -Wextra -O2 -fPIC -m64 -g # Added -fPIC for Position-Independent Code
TARGET = dna_tool
SOURCES = dna_tool.c
OBJECTS = $(SOURCES:.c=.o)

# Target for Windows DLL
all: $(TARGET).dll

$(TARGET).dll: $(OBJECTS)
	$(CC) -shared -o $(TARGET).dll $(OBJECTS) -Wl,--out-implib,lib$(TARGET).a
	$(CC) -o $(TARGET) $(OBJECTS)
	mv $(TARGET) ../

# Rule to compile object files
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

# Clean up build files
clean:
	rm -f *.o *.dll *.a

.PHONY: all clean
