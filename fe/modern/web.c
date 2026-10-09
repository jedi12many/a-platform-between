/*
 * The modern front end in a browser (fe/modern/modern.h), compiled to WebAssembly with
 * Emscripten: fe/modern/web/index.html draws the screen on a canvas and passes in keys
 * and clicks. The game waits for a key with emscripten_sleep (Asyncify), so the VM runs
 * as it does everywhere else, one choice at a time.
 *
 * The page calls web_start with a Departure, one of the page's bundled directories
 * (/departures/the-fare, ...). Saves go to /saves/DEPARTURE, kept in the browser's
 * IndexedDB. Given a choices file, it plays from it the way the desktop's --choices
 * does and writes the transcript to the console: tests/modern/check_web.cjs plays the
 * browser build that way.
 */
#include <string.h>
#include <sys/stat.h>

#include <emscripten.h>

#include "modern.h"

static uint32_t fb[SCR_W * SCR_H];
static uint8_t rgba[SCR_W * SCR_H * 4];

EM_JS(void, js_draw, (const uint8_t *pixels), {
    Module.drawScreen(HEAPU8.subarray(pixels, pixels + 640 * 400 * 4));
});

EM_JS(int, js_take_key, (void), {
    return Module.keys.length ? Module.keys.shift() : -1;
});

EM_JS(void, js_sync_saves, (void), {
    FS.syncfs(false, function (err) { if (err) console.error("saving failed", err); });
});

void plat_show(void)
{
    int i;

    modern_render(fb);
    for (i = 0; i < SCR_W * SCR_H; ++i) {
        rgba[i * 4] = (uint8_t)(fb[i] >> 16);
        rgba[i * 4 + 1] = (uint8_t)(fb[i] >> 8);
        rgba[i * 4 + 2] = (uint8_t)fb[i];
        rgba[i * 4 + 3] = 255;
    }
    js_draw(rgba);
}

uint16_t plat_key(void)
{
    int k;

    plat_show();
    while ((k = js_take_key()) < 0) emscripten_sleep(20);
    return (uint16_t)k;
}

/* A row of the screen as text, for tests/modern/check_web.cjs to read. */
EMSCRIPTEN_KEEPALIVE const char *web_screen_row(int row)
{
    static char text[SCR_COLS + 1];
    int i;

    if (row < 0 || row >= SCR_ROWS) return "";
    for (i = 0; i < SCR_COLS; ++i) text[i] = (char)(scr_char[row][i] & 0x7F);
    text[SCR_COLS] = '\0';
    return text;
}

void plat_wait(unsigned ms)
{
    plat_show();
    emscripten_sleep(ms);
}

/* Sound: the page takes the music's samples (fe/modern/sound.c) a buffer at a time, on
 * its own thread, between the game's waits: so no lock. Browsers only let sound start
 * after a key or a click; the page wakes it on the next one (index.html). */
static int16_t audio_buffer[4096];

EMSCRIPTEN_KEEPALIVE int16_t *web_audio_fill(int n)
{
    if (n > (int)(sizeof(audio_buffer) / sizeof(audio_buffer[0]))) n = 0;
    sound_mix(audio_buffer, n);
    return audio_buffer;
}

EM_JS(void, js_audio_start, (int rate), {
    try {
        var Context = window.AudioContext || window.webkitAudioContext;
        var audio = Module.audio = new Context({ sampleRate: rate });
        var pull = function (n) {
            var at = _web_audio_fill(n) >> 1;
            var out = new Float32Array(n);
            for (var i = 0; i < n; i++) out[i] = HEAP16[at + i] / 32768;
            return out;
        };
        if (audio.audioWorklet && window.isSecureContext) {
            /* An AudioWorklet plays what the page sends it; the page keeps it a tenth of a
             * second ahead, from a timer that runs between the game's waits. */
            var feed = "class Feed extends AudioWorkletProcessor {" +
                " constructor() { super(); this.queue = []; this.at = 0;" +
                "  this.port.onmessage = (e) => this.queue.push(e.data); }" +
                " process(inputs, outputs) { const out = outputs[0][0];" +
                "  for (let i = 0; i < out.length; i++) {" +
                "   if (!this.queue.length) { out[i] = 0; continue; }" +
                "   const b = this.queue[0]; out[i] = b[this.at++];" +
                "   if (this.at >= b.length) { this.queue.shift(); this.at = 0; } }" +
                "  return true; } }" +
                "registerProcessor('apb-feed', Feed);";
            var url = URL.createObjectURL(new Blob([feed], { type: "application/javascript" }));
            audio.audioWorklet.addModule(url).then(function () {
                var node = Module.audioNode = new AudioWorkletNode(audio, "apb-feed");
                node.connect(audio.destination);
                var sent = 0;
                var ahead = Math.floor(rate / 10);
                setInterval(function () {
                    var played = Math.floor(audio.currentTime * rate);
                    if (sent < played) sent = played;           /* it ran dry: start again */
                    while (sent - played < ahead) {
                        node.port.postMessage(pull(1024));
                        sent += 1024;
                    }
                }, 25);
            });
        } else {
            var node = Module.audioNode = audio.createScriptProcessor(2048, 0, 1);
            node.onaudioprocess = function (e) {
                e.outputBuffer.getChannelData(0).set(pull(e.outputBuffer.length));
            };
            node.connect(audio.destination);
        }
        audio.resume();
    } catch (e) { /* no sound here: play on in silence */ }
});

void plat_audio_start(void)
{
    js_audio_start(SFX_RATE);
}

void plat_audio_lock(void) {}
void plat_audio_unlock(void) {}

void plat_saved(void)
{
    js_sync_saves();
}

/* Start a trip: called from the page (Module.start), once. `choices` is "" to play by
 * hand, or a file to play from. (Not main(): the page decides when, and Debian's
 * Emscripten drops main() when the page calls it itself.) */
EMSCRIPTEN_KEEPALIVE void web_start(const char *departure, unsigned seed, const char *choices)
{
    static char dir[256];
    static char save_dir[256];
    FILE *choice_file = NULL;

    snprintf(dir, sizeof(dir), "/departures/%s", departure);
    snprintf(save_dir, sizeof(save_dir), "/saves/%s", departure);
    mkdir(save_dir, 0777);
    if (choices[0]) choice_file = fopen(choices, "r");
    modern_setup(dir, save_dir, choice_file, choice_file ? stdout : NULL);
    modern_play((uint16_t)seed);
    plat_show();
    fflush(stdout);
    EM_ASM({ if (Module.onTripOver) Module.onTripOver(); });
}
