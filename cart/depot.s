; A Departure's depot and its cars (docs/vm-spec.md, "The depot", "Cars"; the C version is
; vm/vm.c's load_depot and load_car): fetched from their assets (tools/cart/departure.py),
; copied to DEPOT_AT and CAR_AT, and checked; and the scenes, entered. Where everything is
; in them is kept here as addresses, for the VM (vm.s) and the strings (expand.s).

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export vm_open, scene_enter
        .export kind, dep_id, level_max, flag_count, var_count, var_init
        .export pair_count, pairs_at, picture_count, pictures_at, music_count, music_at
        .export encounter_count, encounters_at
        .export car_index, car_title, code_len, code_end, string_count, offsets_at
        .export strings_at, car_end, picture_asset
        .import asset_fetch, ram_copy, vm_fail, failed

CODE_AT         = CAR_AT + 9        ; a car's code
CODE_OFF        = 9
SCENE_CARS      = 64                ; a scene's car is one of these
MUSIC_MAX       = 32
TUNE_NAME_MAX   = 20

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; vm_open: the depot, from its asset (its length, the asset of its first picture, then
; it: tools/cart/departure.py), checked as load_depot checks it: its header; the pair
; table, each pair made of bytes and pairs before it; the pictures', encounters' and (v1)
; tunes' lists end to end, inside it, with nothing after; every scene's car under 64.
;   Before:  $01 = $35.
;   After:   C clear; or C set: the VM has failed (vm.s, vm_fail), and said why.
;   Changes: A, X, Y; zp_src, zp_dst, zp_len; zp_t0-zp_t3; assets.s's zero page.
vm_open:
        lda #0                      ; (a failure before is forgotten)
        sta failed
        lda #$FF
        sta car_index
        lda #ASSET_DEPOT
        jsr asset_fetch
        bcs @lost
        lda STAGING + 2             ; the asset of its first picture
        sta picture_asset
        lda STAGING                 ; its length: DEPOT_MAX at most
        sta zp_len
        lda STAGING + 1
        sta zp_len + 1
        lda zp_len
        cmp #<(DEPOT_MAX + 1)
        lda zp_len + 1
        sbc #>(DEPOT_MAX + 1)
        bcc @fits
@lost:  lda #<msg_no_depot
        ldx #>msg_no_depot
        jmp vm_fail
@fits:  lda zp_len                  ; depot_end: just past it
        clc
        adc #<DEPOT_AT
        sta depot_end
        lda zp_len + 1
        adc #>DEPOT_AT
        sta depot_end + 1
        lda #<(STAGING + 3)
        sta zp_src
        lda #>(STAGING + 3)
        sta zp_src + 1
        lda #<DEPOT_AT
        sta zp_dst
        lda #>DEPOT_AT
        sta zp_dst + 1
        jsr ram_copy
        ; "DP", version 0 or 1, and 21 bytes at least.
        lda depot_end + 1
        cmp #>(DEPOT_AT + 21)
        bne @long
        lda depot_end
        cmp #<(DEPOT_AT + 21)
        bcc @not_depot
@long:  lda DEPOT_AT
        cmp #$44                    ; (bytes, not characters: "DP" in ASCII)
        bne @not_depot
        lda DEPOT_AT + 1
        cmp #$50
        bne @not_depot
        lda DEPOT_AT + 2
        cmp #2
        bcc @header
@not_depot:
        lda #<msg_not_depot
        ldx #>msg_not_depot
        jmp vm_fail
@header:
        sta version
        lda DEPOT_AT + 3
        sta kind
        lda DEPOT_AT + 4
        sta dep_id
        lda DEPOT_AT + 5
        sta dep_id + 1
        lda DEPOT_AT + 10
        sta level_max
        lda DEPOT_AT + 11
        sta flag_count
        lda DEPOT_AT + 12
        sta flag_count + 1
        lda DEPOT_AT + 13
        sta var_count
        lda DEPOT_AT + 14
        sta scene_count
        lda DEPOT_AT + 15
        sta scene_count + 1
        lda DEPOT_AT + 16
        sta start_scene
        lda DEPOT_AT + 17
        sta start_scene + 1
        ; kind 0-2, flags 512 at most, vars 128, scenes 1-1024, the start one of them, the
        ; title 40 bytes.
        lda kind
        cmp #3
        bcs @bad_header
        lda flag_count
        cmp #<513
        lda flag_count + 1
        sbc #>513
        bcs @bad_header
        lda var_count
        cmp #129
        bcs @bad_header
        lda scene_count
        ora scene_count + 1
        beq @bad_header
        lda scene_count
        cmp #<1025
        lda scene_count + 1
        sbc #>1025
        bcs @bad_header
        lda start_scene
        cmp scene_count
        lda start_scene + 1
        sbc scene_count + 1
        bcs @bad_header
        lda DEPOT_AT + 20
        cmp #41
        bcc @sizes
@bad_header:
        lda #<msg_bad_header
        ldx #>msg_bad_header
        jmp vm_fail
@sizes: ; The vars' start values after the title; the scene directory after them, 3 bytes
        ; a scene; then the pair table.
        clc
        adc #<(DEPOT_AT + 21)
        sta var_init
        lda #>(DEPOT_AT + 21)
        adc #0
        sta var_init + 1
        lda var_init
        clc
        adc var_count
        sta dir_at
        sta zp_t0
        lda var_init + 1
        adc #0
        sta dir_at + 1
        sta zp_t1
        lda scene_count             ; + 3 x scenes (3072 at most)
        asl a
        sta zp_t2
        lda scene_count + 1
        rol a
        sta zp_t3
        lda zp_t2
        clc
        adc scene_count
        sta zp_t2
        lda zp_t3
        adc scene_count + 1
        sta zp_t3
        jsr at_add
        jsr at_inside
        bcc @pairs
        lda #<msg_short
        ldx #>msg_short
        jmp vm_fail
@pairs: jsr at_byte                 ; the pairs: 128 at most, 2 bytes each
        sta pair_count
        lda zp_t0
        sta pairs_at
        lda zp_t1
        sta pairs_at + 1
        lda pair_count
        cmp #129
        bcs @bad_pairs
        asl a
        sta zp_t2
        lda #0
        rol a
        sta zp_t3
        jsr at_add
        jsr at_inside
        bcc @forward
@bad_pairs:
        lda #<msg_bad_pairs
        ldx #>msg_bad_pairs
        jmp vm_fail
@forward:
        jsr pairs_back
        bcc @pictures
        lda #<msg_forward
        ldx #>msg_forward
        jmp vm_fail
@pictures:
        jsr at_byte                 ; the pictures' names: a length, then it
        sta picture_count
        lda zp_t0
        sta pictures_at
        lda zp_t1
        sta pictures_at + 1
        ldx picture_count
        beq @pictured
@picture:
        jsr at_inside
        bcs @bad_pictures
        jsr at_skip
        dex
        bne @picture
@pictured:
        jsr at_inside
        bcc @encounters
@bad_pictures:
        lda #<msg_bad_pictures
        ldx #>msg_bad_pictures
        jmp vm_fail
@encounters:
        ; The encounters: 32 at most, each its length (2 bytes) and then it, inside the
        ; depot. What's in one is checked when a fight uses it.
        jsr at_byte
        cmp #MAX_ENCOUNTERS + 1
        bcc @count
        jmp @bad_encounters
@count: sta encounter_count
        ldy zp_t0                   ; (the first one's length)
        sty encounters_at
        ldy zp_t1
        sty encounters_at + 1
        tax
        beq @tunes
@encounter:
        jsr at_byte
        sta zp_t2
        jsr at_byte
        sta zp_t3
        jsr at_in_or_end
        bcs @bad_encounters
        jsr at_add
        bcs @bad_encounters
        jsr at_in_or_end
        bcs @bad_encounters
        dex
        bne @encounter
@tunes: lda zp_t0
        sta music_at
        lda zp_t1
        sta music_at + 1
        lda #0
        sta music_count
        lda version                 ; v1: the tunes' names, 32 at most, each 1-20 bytes
        beq @ends
        jsr at_inside
        bcs @bad_music
        jsr at_byte
        cmp #MUSIC_MAX + 1
        bcs @bad_music
        sta music_count
        lda zp_t0
        sta music_at
        lda zp_t1
        sta music_at + 1
        ldx music_count
        beq @ends
@tune:  jsr at_inside
        bcs @bad_music
        ldy #0
        lda (zp_t0), y
        beq @bad_music
        cmp #TUNE_NAME_MAX + 1
        bcs @bad_music
        jsr at_skip
        dex
        bne @tune
@ends:  lda zp_t0                   ; nothing after
        cmp depot_end
        bne @trailing
        lda zp_t1
        cmp depot_end + 1
        bne @trailing
        jmp scene_cars
@bad_encounters:
        lda #<msg_bad_encounters
        ldx #>msg_bad_encounters
        jmp vm_fail
@bad_music:
        lda #<msg_bad_music
        ldx #>msg_bad_music
        jmp vm_fail
@trailing:
        lda #<msg_trailing
        ldx #>msg_trailing
        jmp vm_fail

MAX_ENCOUNTERS = 32

; scene_cars: the end of vm_open: every scene's car under 64.
scene_cars:
        lda dir_at
        sta zp_t0
        lda dir_at + 1
        sta zp_t1
        lda scene_count
        sta zp_t2
        lda scene_count + 1
        sta zp_t3
@scene: ldy #0
        lda (zp_t0), y
        cmp #SCENE_CARS
        bcs @bad
        lda zp_t0
        clc
        adc #3
        sta zp_t0
        bcc @same
        inc zp_t1
@same:  lda zp_t2                   ; one fewer to go
        bne @low
        dec zp_t3
@low:   dec zp_t2
        lda zp_t2
        ora zp_t3
        bne @scene
        clc
        rts
@bad:   lda #<msg_bad_directory
        ldx #>msg_bad_directory
        jmp vm_fail

; pairs_back: C clear if each pair's two bytes are under $80 + its own number (bytes, or
; pairs made before it); else C set. Changes A, X, Y; zp_t2, zp_t3.
pairs_back:
        lda pairs_at
        sta zp_t2
        lda pairs_at + 1
        sta zp_t3
        ldx #0
@pair:  cpx pair_count
        beq @good
        txa
        ora #$80
        sta forward
        ldy #0
        lda (zp_t2), y
        cmp forward
        bcs @bad
        iny
        lda (zp_t2), y
        cmp forward
        bcs @bad
        lda zp_t2
        clc
        adc #2
        sta zp_t2
        bcc @same
        inc zp_t3
@same:  inx
        bne @pair                   ; (always: 128 at most)
@good:  clc
@bad:   rts

; The walk through the depot: `at` is zp_t0/zp_t1.

; at_byte: A = the byte at `at`, and `at` past it. Changes A, Y.
at_byte:
        ldy #0
        lda (zp_t0), y
        inc zp_t0
        bne @same
        inc zp_t1
@same:  rts

; at_skip: past a name: its length byte, then that many. Changes A, Y.
at_skip:
        jsr at_byte
        clc
        adc zp_t0
        sta zp_t0
        bcc @same
        inc zp_t1
@same:  rts

; at_add: `at` + zp_t2/zp_t3. After: C set if it went past $FFFF. Changes A.
at_add:
        lda zp_t0
        clc
        adc zp_t2
        sta zp_t0
        lda zp_t1
        adc zp_t3
        sta zp_t1
        rts

; at_inside: C clear if `at` is inside the depot (before its end). Changes A.
at_inside:
        lda zp_t0
        cmp depot_end
        lda zp_t1
        sbc depot_end + 1
        rts

; at_in_or_end: C clear if `at` is inside the depot or just past it. Changes A.
at_in_or_end:
        lda depot_end
        cmp zp_t0
        lda depot_end + 1
        sbc zp_t1
        bcc @past
        clc
        rts
@past:  sec
        rts

; ----------------------------------------------------------------------------------------
; scene_enter: into a scene (vm.c's enter): its car loaded, if it isn't, and on from just
; after its menu offset.
;   Takes:   A/X = the scene (low/high).
;   After:   C clear and zp_ip there; or C set: the VM has failed.
;   Changes: A, X, Y; zp_ip; zp_t0-zp_t3; and load_car's.
scene_enter:
        sta zp_t0
        stx zp_t1
        cmp scene_count
        txa
        sbc scene_count + 1
        bcc @scene
        lda #<msg_bad_scene
        ldx #>msg_bad_scene
        jmp vm_fail
@scene: lda zp_t0                   ; its entry: dir_at + 3 x scene
        asl a
        sta zp_t2
        lda zp_t1
        rol a
        sta zp_t3
        lda zp_t2
        clc
        adc zp_t0
        sta zp_t2
        lda zp_t3
        adc zp_t1
        sta zp_t3
        lda zp_t2
        clc
        adc dir_at
        sta zp_t2
        lda zp_t3
        adc dir_at + 1
        sta zp_t3
        ldy #1                      ; its offset in its car, kept: load_car changes zp_t*
        lda (zp_t2), y
        sta entry
        iny
        lda (zp_t2), y
        sta entry + 1
        ldy #0
        lda (zp_t2), y
        cmp car_index
        beq @loaded
        jsr load_car
        bcc @loaded
        rts
@loaded:
        lda entry                   ; on from offset + 2 (past the menu's offset); the VM
        clc                         ; checks it's inside the code before it runs it
        adc #<(CODE_AT + 2)
        sta zp_ip
        lda entry + 1
        adc #>(CODE_AT + 2)
        sta zp_ip + 1
        bcs @off                    ; (past $FFFF: it'd look inside)
        clc
        rts
@off:   lda #<msg_off_code
        ldx #>msg_off_code
        jmp vm_fail

; ----------------------------------------------------------------------------------------
; load_car: a car, from its asset, checked (vm.c's load_car): "CR", its number, its code
; and strings inside it.
;   Takes:   A = the car (0-63).
;   After:   C clear; or C set: the VM has failed.
;   Changes: A, X, Y; zp_src, zp_dst, zp_len; zp_t0, zp_t1; assets.s's zero page.
load_car:
        sta car_index
        clc
        adc #ASSET_CAR0
        jsr asset_fetch
        bcs @lost
        lda STAGING                 ; its length: CAR_MAX at most
        sta zp_len
        lda STAGING + 1
        sta zp_len + 1
        lda zp_len
        cmp #<(CAR_MAX + 1)
        lda zp_len + 1
        sbc #>(CAR_MAX + 1)
        bcc @fits
@lost:  lda #<msg_no_car
        ldx #>msg_no_car
        jmp vm_fail
@fits:  lda zp_len
        sta car_len
        clc
        adc #<CAR_AT
        sta car_end
        lda zp_len + 1
        sta car_len + 1
        adc #>CAR_AT
        sta car_end + 1
        lda #<(STAGING + 2)
        sta zp_src
        lda #>(STAGING + 2)
        sta zp_src + 1
        lda #<CAR_AT
        sta zp_dst
        lda #>CAR_AT
        sta zp_dst + 1
        jsr ram_copy
        lda car_len + 1             ; 9 bytes at least, "CR", its number
        bne @long
        lda car_len
        cmp #CODE_OFF
        bcc @bad_header
@long:  lda CAR_AT
        cmp #$43
        bne @bad_header
        lda CAR_AT + 1
        cmp #$52
        bne @bad_header
        lda CAR_AT + 2
        cmp car_index
        beq @header
@bad_header:
        lda #<msg_car_header
        ldx #>msg_car_header
        jmp vm_fail
@header:
        lda CAR_AT + 3
        sta car_title
        lda CAR_AT + 4
        sta car_title + 1
        lda CAR_AT + 5
        sta code_len
        lda CAR_AT + 6
        sta code_len + 1
        lda CAR_AT + 7
        sta string_count
        lda CAR_AT + 8
        sta string_count + 1
        ; code_len <= car_len, strings <= 1024, 9 + code_len + 2 x strings <= car_len.
        lda car_len
        cmp code_len
        lda car_len + 1
        sbc code_len + 1
        bcc @bad_sizes
        lda string_count
        cmp #<1025
        lda string_count + 1
        sbc #>1025
        bcs @bad_sizes
        lda code_len                ; code_end: CODE_AT + code_len (under $C000)
        clc
        adc #<CODE_AT
        sta code_end
        sta offsets_at
        lda code_len + 1
        adc #>CODE_AT
        sta code_end + 1
        sta offsets_at + 1
        lda string_count            ; strings_at: offsets_at + 2 x strings
        asl a
        sta zp_t0
        lda string_count + 1
        rol a
        sta zp_t1
        lda offsets_at
        clc
        adc zp_t0
        sta strings_at
        lda offsets_at + 1
        adc zp_t1
        sta strings_at + 1
        lda car_end                 ; strings_at <= car_end
        cmp strings_at
        lda car_end + 1
        sbc strings_at + 1
        bcc @bad_sizes
        clc
        rts
@bad_sizes:
        lda #<msg_car_sizes
        ldx #>msg_car_sizes
        jmp vm_fail

; What goes wrong (vm.c's words: error messages are the platform's, and these are ASCII).
msg_no_depot:       .byte "can't load DEPOT", 0
msg_not_depot:      .byte "not a v0 or v1 depot", 0
msg_bad_header:     .byte "bad depot header", 0
msg_short:          .byte "depot too short", 0
msg_bad_pairs:      .byte "bad pair table", 0
msg_forward:        .byte "pair refers forward", 0
msg_bad_pictures:   .byte "bad picture list", 0
msg_bad_encounters: .byte "bad encounter list", 0
msg_bad_music:      .byte "bad music list", 0
msg_trailing:       .byte "depot has trailing bytes", 0
msg_bad_directory:  .byte "bad scene directory", 0
msg_bad_scene:      .byte "bad scene", 0
msg_off_code:       .byte "ran off the code", 0
msg_no_car:         .byte "can't load car", 0
msg_car_header:     .byte "bad car header", 0
msg_car_sizes:      .byte "bad car sizes", 0

        .segment "BSS"
version:        .res 1
picture_asset:  .res 1              ; the asset of the depot's first picture
kind:           .res 1              ; 0 official, 1 a Branch Line, 2 a Siding
dep_id:         .res 2
level_max:      .res 1
flag_count:     .res 2
var_count:      .res 1
scene_count:    .res 2
start_scene:    .res 2
depot_end:      .res 2              ; addresses, from here on
var_init:       .res 2
dir_at:         .res 2
pair_count:     .res 1
pairs_at:       .res 2
forward:        .res 1
picture_count:  .res 1
pictures_at:    .res 2
encounter_count: .res 1            ; the depot's encounters: how many, and where the first
encounters_at:  .res 2              ; one's length is (each is its length, then it)
music_count:    .res 1
music_at:       .res 2
entry:          .res 2
car_index:      .res 1              ; the car loaded ($FF: none)
car_len:        .res 2
car_end:        .res 2
car_title:      .res 2              ; its title's string ($FFFF: none)
code_len:       .res 2
code_end:       .res 2
string_count:   .res 2
offsets_at:     .res 2
strings_at:     .res 2

        .export start_scene
