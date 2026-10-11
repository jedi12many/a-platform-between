/* A password a line on stdin: what the rules core makes of it, a line on stdout: "ok",
 * "length", "symbol", "line N", "checksum" or "version". A Boarding Pass is told from a
 * Passport by its first symbol, as the boarding desk does (tests/passport/check_refusals.py).
 */
#include <stdio.h>
#include <string.h>
#include "apb.h"

static const char *const names[] = { "ok", "range", "length", "symbol", "line", "checksum",
                                     "version" };

int main(void)
{
    static char text[1024];
    apb_character ch;
    apb_pass pass;
    uint8_t bad = 0;
    uint8_t result;

    while (fgets(text, sizeof(text), stdin)) {
        text[strcspn(text, "\n")] = '\0';
        if (apb_password_kind(text) == APB_KIND_PASS) {
            result = apb_pass_decode(text, &pass, &ch, &bad);
        } else {
            result = apb_passport_decode(text, &ch, &bad);
        }
        if (result == APB_PP_LINE_CHECK) {
            printf("line %u\n", (unsigned)bad);
        } else {
            printf("%s\n", result < 7 ? names[result] : "?");
        }
    }
    return 0;
}
