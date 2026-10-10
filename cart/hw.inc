; The C64's chips and the EasyFlash: the registers the cartridge uses (docs/cartridge.md).
; Names only: no code, no storage.

; ------------------------------------------------------------------ the CPU's port
CPU_DDR         = $00
CPU_PORT        = $01
PORT_GAME       = $35           ; RAM everywhere but the I/O: how the game runs
PORT_CART       = $37           ; the cartridge (and the KERNAL, never called) in
PORT_KERNAL     = $36           ; the KERNAL and the I/O in, RAM at $8000-$BFFF: a load
PORT_ALL_RAM    = $34           ; RAM everywhere: writes to $D000-$DFFF reach the RAM

; ------------------------------------------------------------------ the VIC-II
VIC_SPR_ENA     = $D015
VIC_CTRL1       = $D011         ; text $1B, bitmap $3B (raster bit 8 always 0 here)
VIC_RASTER      = $D012
VIC_CTRL2       = $D016         ; hires $08, multicolour $18 (40 columns)
VIC_MEM         = $D018
VIC_IRQ         = $D019
VIC_IRQ_ENA     = $D01A
VIC_BORDER      = $D020
VIC_BACK        = $D021
VIC_MC1         = $D022
VIC_MC2         = $D023
VIC_SPR_MC1     = $D025
VIC_SPR_MC2     = $D026
COLOUR_RAM      = $D800

CTRL1_TEXT      = $1B
CTRL1_BITMAP    = $3B
CTRL1_BLANK     = $0B           ; the screen off (while it's set up)
CTRL2_HIRES     = $08
CTRL2_MULTI     = $18

; ------------------------------------------------------------------ the SID
SID             = $D400         ; 25 registers

; ------------------------------------------------------------------ the CIAs
CIA1_PRA        = $DC00
CIA1_PRB        = $DC01
CIA1_DDRA       = $DC02
CIA1_DDRB       = $DC03
CIA1_ICR        = $DC0D
CIA1_CRA        = $DC0E
CIA1_CRB        = $DC0F
CIA2_PRA        = $DD00         ; bits 0-1: the VIC's bank, inverted (%00 is bank 3)
CIA2_DDRA       = $DD02
CIA2_ICR        = $DD0D
CIA2_CRA        = $DD0E
CIA2_CRB        = $DD0F

; ------------------------------------------------------------------ the EasyFlash
EF_BANK         = $DE00         ; write only: the bank, 0-63
EF_CONTROL      = $DE02         ; write only: the mode
EF_RAM          = $DF00         ; 256 bytes of RAM, there while the I/O is
EF_OFF          = $04
EF_ULTIMAX      = $05           ; as it boots: ROML at $8000, ROMH at $E000
EF_8K           = $06
EF_16K          = $07           ; ROML at $8000, ROMH at $A000
EF_LED          = $80

; ------------------------------------------------------------------ the KERNAL (disks only)
KERNAL_SETLFS   = $FFBA
KERNAL_SETNAM   = $FFBD
KERNAL_LOAD     = $FFD5
KERNAL_READST   = $FFB7
KERNAL_OPEN     = $FFC0
KERNAL_CLOSE    = $FFC3
KERNAL_CHKIN    = $FFC6
KERNAL_CLRCHN   = $FFCC
KERNAL_CHRIN    = $FFCF
KERNAL_DEVICE   = $BA           ; the device it last used: the one we were loaded from

; ------------------------------------------------------------------ vectors
VEC_IRQ_KERNAL  = $0314         ; where the KERNAL's interrupt goes, while it's in
VEC_NMI_KERNAL  = $0318
VEC_NMI         = $FFFA         ; the 6502's own, in the RAM under the KERNAL
VEC_RESET       = $FFFC
VEC_IRQ         = $FFFE
