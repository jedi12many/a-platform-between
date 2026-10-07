# Picture prompts

Prompts for drawing the game's pictures with an image model (they were written for
Gemini). Paste the **style block** first, then one **picture** prompt. Ask for each
picture separately; make a few and keep the best.

The model's picture goes in the Departure's `pictures/gemini/NAME.jpg`, and the
Departure's `pictures/paint.py` fits it to the C64 with `tools/c64fit.py`, choosing the
part to keep (`--box`) and painting over anything that needs it: see
`content/s1/00-the-fare/pictures/paint.py` and [c64.md](c64.md), "Pictures".

What's learned so far, from The Fare:
- **Ask for 10:3.** The picture is a wide strip; a square picture loses half of itself
  (the concourse's departure board doesn't fit).
- **Fewer things, bigger.** At 160 x 96 a crowded scene turns to mud: the Buffer Stop's
  knight vanished into the crowd and the panelling, and the rainy platform's bench into
  the grey. Ask for one subject, a plain background and strong contrast.
- **Words are painted by the game.** Ask for blank signs; the model's lettering is
  nonsense anyway, and too small to read.
- **Deep colours shift.** The C64's purple is lighter than a velvet purple, so it fits
  to blue; `paint.py` puts it back.

Big flat shapes and strong silhouettes come through well; fine detail, gradients and
small text don't. Faces are tiny at this size (a head is about 8 pixels across), so
people work best as silhouettes, seen from behind, or lit by a lamp.

---

## Style block (paste this first, every time)

> Pixel art for a 1980s Commodore 64 adventure game, in the style of the best C64
> multicolour title screens. A wide landscape scene, aspect ratio exactly 10:3 (for
> example 2000 x 600 pixels), drawn as if it were 160 x 96 large chunky pixels, each pixel
> twice as wide as it is tall. Use only these 16 colours, in flat fills:
> #000000 black, #FFFFFF white, #68372B dark red, #70A4B2 cyan, #6F3D86 purple,
> #588D43 green, #352879 dark blue, #B8C76F yellow, #6F4F25 orange-brown, #433900 dark
> brown, #9A6759 pink, #444444 dark grey, #6C6C6C grey, #9AD284 light green,
> #6C5EB5 light blue, #959595 light grey.
> Most of the picture should use only three or four of these colours, with small accents
> of others. Shade with checkerboard dithering, never smooth gradients. No anti-aliasing,
> no blur, no outlines thinner than a pixel, no text, no frame, no border, no UI. Bold
> silhouettes, clear readable shapes, moody lighting, a melancholy and slightly strange
> tone: a railway station between worlds, for the dead.

---

## The Fare

**static.png**
> The moment of death: a full frame of grey television static, black, dark grey and light
> grey noise, with two brighter rolling bands across it. From the top right corner a
> glowing white hand reaches down into the static, fingers spread, as if to pull someone
> out. A soft white light around the hand.

**platform_bench.png**
> A railway platform under a Victorian roof of green cast-iron arches and cracked glass.
> Beyond the glass there is no sky, only a slow grey shimmer like rain falling the wrong
> way. A white enamel sign hangs from the ironwork (leave it blank). In the centre of the
> platform, an empty wooden bench with dark red slats and iron legs. A white safety line
> along the platform edge. Greys and green, quiet, empty.

**concourse.png**
> The great hall of a grand railway station at night: iron arches overhead, glass roof,
> a tiled floor worn into paths. High in the centre hangs a black departure board with
> rows of yellow flip-letters. Arched doorways lead off to the platforms. On the right, warm
> yellow light spills from the open door of a small bar under a sign showing a rail track
> ending in a red buffer stop. A few travellers in black silhouette cross the floor, one
> with a suitcase. Two hanging lamps glow yellow. Mostly black and greys, yellow light.

**buffer_stop.png**
> Inside a cosy, crowded station bar with brown wood panelling and lamplight. Behind the
> polished bar stands a bartender who is a living tree: bark body, a leafy green crown,
> faintly glowing green eyes, a twig-hand holding a rag that keeps catching fire. Shelves
> of colourful bottles behind. On the left, a knight in rusted red plate armour argues with
> a small cloud of white moths. On the right, a translucent cyan figure made of glass
> drinks a glass of pale yellow light. Browns and orange, warm.

**stationmaster.png**
> A very tall, polite, faceless figure in a long purple velvet coat with brass buttons and
> a peaked station-master's cap, standing behind a table in a dark office. Its face is
> only shadow, with two faint points of light. On the table, a large open ledger with a
> name half written, a pen in an inkwell, white gloves. Behind: walls of wooden
> pigeonholes holding old tickets, a round white station clock, a brass lamp with a green
> shade. Black, purple and dark grey, with brass-yellow accents.

---

## Eighteen Minutes (a dying space station in a time loop)

**dock.png**
> The arrival dock of a space station: scuffed white wall panels bathed in pulsing red
> klaxon light. A large round viewport shows black space, stars, a swollen red sun, and a
> dead freighter tumbling end over end. On the wall, a small black screen showing a red
> countdown. The deck floor ends in a yellow-and-black hazard stripe where a train has just
> vanished. Light grey, dark grey, black, with red.

**medbay.png**
> A stark white space-station medical bay. On a bed, an engineer lies wrapped in pale
> cyan cooling gel, wearing an oxygen mask. A doctor in a white coat with a dark stain,
> dark hair pinned up, bends over him working with black gloves. A black monitor on the
> wall shows a green heartbeat line. A red cross on the wall. White, light grey and black.

**hydroponics.png**
> A hydroponics bay on a space station: dark room, rows of green crop plants in long
> brown troughs receding into the distance, under violet grow-lamps that cast purple cones
> of light. In the foreground a woman with red hair sits cross-legged in the soil, calm,
> not running anywhere, her face lit by the lamps. Black, green, brown and purple.

**command.png**
> The command deck of a space station under a glass dome full of stars. A ring of dead
> grey consoles; only one still glows cyan. A woman captain in a long dark blue coat,
> grey hair pinned up, seen from behind, shakes her fist at the ceiling, where a single
> yellow eye looks calmly down: the station AI. At the back, a door to the captain's
> quarters stands half open. Black, dark grey and grey, with blue, cyan and yellow.

**reactor.png**
> A reactor room like a cathedral of heat: dark red walls with orange ribs climbing into
> blackness. In the centre a tall column of white-hot light behind a caged glass window.
> To the left, a maintenance drone the size of a fridge with a cyan eye and a welding arm.
> To the right, a black console with a yellow warning screen (leave it blank). Dark red,
> black and orange, with yellow and white.

**safe.png**
> A small captain's cabin on a space station: a bunk with a dark blue blanket, a sepia
> photograph of a young girl on the wall, and a wall safe standing open. Inside the safe, a
> frosted cyan cylinder, the size of a thermos, giving off cold white mist: a seed vault.
> Dark grey, black and grey, with blue, cyan and pale yellow.

---

## The Deep Yards (a descent under the station)

**yards.png**
> The far end of a freight rail yard at night, past the last yellow lamp. A dark square
> shaft drops into the ground under a tall iron headframe with a winding wheel. A rusted
> dark-red cage lift hangs over the shaft on its cable. To the right, its operator sits on
> a stool: a hunched man who seems made mostly of rust and patience. Black, dark grey and
> grey, with rust red and lamp yellow.

**bottom.png**
> The tenth floor deep underground: an old brick vault, rails running in and stopping at a
> large red railway buffer stop with a blank grey board on it (leave it blank; the game
> paints the words). Beside it, a cage lift waits with a small yellow lamp lit. Black, dark
> grey and grey, with red and a little yellow.
