/*
 * Season 1 registry: item and Echo IDs.
 *
 * Append-only. An ID, once shipped, is never reused or changed; Passports in the
 * wild depend on it. IDs are 10 bits (1..1023); 0 means "empty".
 */
#ifndef APB_REGISTRY_H
#define APB_REGISTRY_H

/* ------------------------------------------------------------ items */

#define APB_ITEM_NONE            0
#define APB_ITEM_PULSE_RIFLE     1   /* ranged  t4 energy  TL8 ML0 */
#define APB_ITEM_BALLISTIC_WEAVE 2   /* armor   t3 kinetic TL8 ML0 */
#define APB_ITEM_MED_SCANNER     3   /* tool    t2 mind    TL7 ML0 */
#define APB_ITEM_HOVER_BIKE      4   /* vehicle t3 kinetic TL8 ML0 */
#define APB_ITEM_RUSTED_SABRE    5   /* melee   t1 kinetic TL3 ML0 */
#define APB_ITEM_MERIDIAN_CORE   6   /* focus   t2 mind    TL8 ML0 (Departure 01) */

/* ----------------------------------------------------------- Echoes */
/* Each Echo lists its states (1..3) and its canon default. */

#define APB_ECHO_MERIDIAN        1   /* Departure 01 */
#define   APB_MERIDIAN_FREED       1
#define   APB_MERIDIAN_WIPED       2   /* canon default */
#define   APB_MERIDIAN_CARRIED     3

#define APB_ECHO_KEPLER_CREW     2   /* Departure 01 */
#define   APB_KEPLER_CREW_SAVED    1
#define   APB_KEPLER_CREW_LOST     2   /* canon default */

#define APB_ECHO_SEED_VAULT      3   /* Departure 01 */
#define   APB_SEED_VAULT_DELIVERED 1   /* canon default */
#define   APB_SEED_VAULT_KEPT      2
#define   APB_SEED_VAULT_DESTROYED 3

#define APB_ECHO_WOLF_PUP        4   /* Departure 02 */
#define   APB_WOLF_PUP_SAVED       1
#define   APB_WOLF_PUP_LEFT        2   /* canon default */
#define   APB_WOLF_PUP_SWORN       3   /* after the grown wolf has answered */

#define APB_ECHO_JACE_CUTTER     5   /* Departure 02 */
#define   APB_JACE_SPARED          1
#define   APB_JACE_KILLED          2   /* canon default */
#define   APB_JACE_RECRUITED       3

#define APB_ECHO_OREN_VEY        6   /* Departure 02 */
#define   APB_OREN_BOARDED         1   /* canon default */
#define   APB_OREN_STAYED          2

#define APB_ECHO_YSOLDE          7   /* Departure 03 */
#define   APB_YSOLDE_BEFRIENDED    1
#define   APB_YSOLDE_EXPOSED       2   /* canon default */
#define   APB_YSOLDE_DESTROYED     3

#define APB_ECHO_LANTERN_COURT   8   /* Departure 03 */
#define   APB_LANTERN_WELCOME      1   /* canon default */
#define   APB_LANTERN_BANISHED     2

#define APB_ECHO_YSOLDE_LEDGER   9   /* Departure 03 */
#define   APB_LEDGER_READ          1
#define   APB_LEDGER_BURNED        2   /* canon default */

#endif
