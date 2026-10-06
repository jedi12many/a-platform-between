#include "apb.h"
#include "names.h"

/*
 * Both cases are spelled out as literals rather than using toupper(): cc65
 * translates literals to PETSCII on the C64, so comparing against literals keeps
 * the mapping identical on every platform.
 */
static const char upper[] = " ABCDEFGHIJKLMNOPQRSTUVWXYZ-'.!?";
static const char lower[] = " abcdefghijklmnopqrstuvwxyz-'.!?";

/* The same alphabet as byte values, so it stays ASCII on every platform. */
static const uint8_t ascii[APB_NAME_SYMBOLS] = {
    32, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83,
    84, 85, 86, 87, 88, 89, 90, 45, 39, 46, 33, 63
};

uint8_t apb_name_ascii(char c)
{
    return ascii[apb_name_index(c)];
}

uint8_t apb_name_index(char c)
{
    uint8_t i;

    for (i = 0; i < APB_NAME_SYMBOLS; ++i) {
        if (upper[i] == c || lower[i] == c) {
            return i;
        }
    }
    return 0;
}

char apb_name_char(uint8_t index)
{
    return upper[index & (APB_NAME_SYMBOLS - 1)];
}

void apb_name_normalize(const char *in, char *out)
{
    uint8_t i = 0;
    uint8_t end = 0;

    while (i < APB_NAME_LEN && in[i] != '\0') {
        out[i] = apb_name_char(apb_name_index(in[i]));
        ++i;
        if (out[i - 1] != ' ') {
            end = i;
        }
    }
    out[end] = '\0';
}
