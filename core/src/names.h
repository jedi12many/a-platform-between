/* Internal: the 32-symbol name alphabet shared by characters and Passports. */
#ifndef APB_NAMES_H
#define APB_NAMES_H

#include <stdint.h>

#define APB_NAME_SYMBOLS 32

/* Index of c in the name alphabet (either case), or 0 (space) if absent. */
uint8_t apb_name_index(char c);
char    apb_name_char(uint8_t index);
/* Copy up to APB_NAME_LEN symbols into out (NUL-terminated, upper case,
 * trailing spaces trimmed). */
void    apb_name_normalize(const char *in, char *out);

#endif
