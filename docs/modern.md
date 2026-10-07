# The modern front end

*Milestone E6. The same game on a desktop (SDL2) and in a browser (WebAssembly), from
one piece of C: `fe/modern/`.*

## Playing it

**Desktop.** `make modern` builds `build/apb-modern` (it needs SDL2: `apt-get install
libsdl2-dev`) and a directory of files for each Departure:

```
./build/apb-modern build/modern/the-fare
./build/apb-modern build/modern/eighteen-minutes
```

**Browser.** `make web` builds `build/web/` (it needs Emscripten: `apt-get install
emscripten`) with both Departures inside. Serve it and open it:

```
python3 -m http.server -d build/web 8000      # then http://localhost:8000/
```

Pick a Departure, then play as on the C64: press a number, or click a menu line. Type
your Passport a line at a time. **S** at a menu saves the trip, and "Pick up a saved
trip" carries on from the save. On the desktop the save goes next to the Departure's
files. In a browser it stays in that browser (IndexedDB), and survives a reload.

## The screen

It's the C64's screen (`docs/c64.md`), drawn sharper. That's on purpose: a writer who
sees a scene in one sees the same scene in all of them.

| Rows | What |
|---|---|
| 0 | the status bar |
| 1–12 | the picture, once the story has shown one (the whole screen is text during a fight) |
| 13–24 | the text window, word-wrapped at 40 columns, with "-- more --" before anything scrolls off unread |

The screen is 640 x 400 pixels: 40 x 25 characters of 16 x 16, from an 8 x 8 font
(`fe/modern/font8x8.h`, the public-domain font8x8) doubled. The window scales it to
fit. Unlike the C64, it has `~`, `_` and braces.

**Pictures** are in full colour. A Departure's `pictures/*.png` become `picNN.apic`
files (`tools/apic.py`): up to 640 x 384 pixels and 256 colours each. They're stretched
to fill rows 1–12, so a 160 x 96 picture, drawn for the C64, has the C64's shape here
too. Real art can be drawn bigger, and the C64 converter will scale it down
(`tools/c64pic.py`).

## How it's built

| File | What |
|---|---|
| `fe/modern/screen.c` | the whole HAL on the 40 x 25 screen: text, menus, typed lines, the battle screen, pictures, files, the start menu and the receipt |
| `fe/modern/render.c` | the screen into a 640 x 400 framebuffer |
| `fe/modern/sdl.c` | the desktop: a window, keys and clicks (SDL2) |
| `fe/modern/web.c`, `fe/modern/web/index.html` | the browser: the page draws the framebuffer on a canvas and queues keys and clicks |

A platform supplies three functions (`fe/modern/modern.h`):
- `plat_key`: wait for a key or a click;
- `plat_show`: show the screen;
- `plat_saved`: a save was written.

The VM waits for the player the same way everywhere: `plat_key` returns when there's a
key. In a browser the C can't block, so it's built with Asyncify. `plat_key` sleeps
(`emscripten_sleep`) until the page has a key; the page carries on meanwhile.

The page starts a trip with the exported `web_start`, not `main`. Debian's Emscripten
(3.1.6) drops `main` when the page decides when to call it.

## Testing

`make test-modern` (`tests/modern/check_modern.py`):

- **Desktop vs C64:** the desktop plays each C64 test route from its choices file, with
  no window (`apb-modern --choices`). Its transcript must be the C64's reviewed one
  (`tests/c64/*.expected`), so the Travel Stamps are the C64's and the terminal's. The
  only differences allowed: the C64 shows `-` for `~` and names pictures by their files.
  - A trip with no Boarding Pass takes its dice from the clock. That reads 0 in the
    C64's emulator, so the desktop plays with `--seed 0`.
  - The save test saves, stops the program, and starts a new one that picks the trip up.
- **Browser vs desktop:** the browser build, in headless Chromium through Playwright
  (`tests/modern/check_web.cjs`), must give the desktop's transcript line for line on
  the same routes. Its save must survive the page being reloaded.
- **Real input:** keys and clicks are pressed on the page, and the screen read back:
  - a click on a menu line picks it;
  - typing, Backspace and Enter reach the boarding desk;
  - the canvas is drawn.

`apb-modern --shots DIR` saves a picture of the screen (PPM) each time the game waits,
to look at.

It needs SDL2, Emscripten, and Node with Playwright (`npm install -g playwright`, then
`npx playwright install chromium`). CI installs all three.

## Not yet

- **A look of its own.** It's the C64's screen, sharper. A wider text column, a
  proportional font, or music would all be the modern build's own, without changing
  the game.
- **Choosing a Departure** on the desktop is the command line; the browser has a page
  of buttons.
- **Mobile.** The page works with a touch to pick menus, but typing a Passport needs a
  keyboard, and nothing brings one up yet.
