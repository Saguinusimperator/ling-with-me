# Window ledge assets

`ling/perch.png` and `ling-heart/perch.png` are independent, transparent six-frame
strips for the standalone Windows app. Original sprite sheets and Pets manifests
are unchanged. Each runtime cell is 192 × 208; the source ledge anchor is (96, 188).
The renderer offsets the resting strip upward by 84 pixels to remove transparent
top padding, giving a display anchor of (96, 104). Standing reactions are scaled
to the same display anchor, so they do not require extra space above the window.

Generated using the built-in imagegen tool on 2026-11-04, then sliced and uniformly
resized into runtime cells. The original generated strips are retained locally
under `build/perch-qa/source/`. Runtime strips are bundled with the app.

Silver prompt:
> Create a transparent PNG sprite strip for this exact blond chibi silver futuristic jumpsuit character. New action: lying prone across an imaginary window top ledge, torso horizontal toward right, head at left turned toward viewer, chin resting on folded forearms, boots behind to right. Cute restful, not standing. Match reference detailed soft illustrated sticker style and identity. Exactly SIX animation frames in ONE horizontal row of six equal square cells, identical scale and fixed position, breathing subtly and blinking (eyes open, open, half closed, closed, half closed, open). Forearms/belly contact with imaginary horizontal ledge at exactly 75% of each cell height; nothing drawn as ledge. Entire body contained in each cell with margin. Transparent background, no shadow platform, no window, no labels, no text, no grid. Output wide 1536x256 strip if possible.

Heart prompt:
> Create exactly SIX animation frames in ONE horizontal strip of six equal cells on transparent background. Match the lying pose and strip arrangement of second reference but use EXACT outfit and character in first reference: blond chibi, white round hat, white shirt, red necktie, navy shorts with red hearts, red sneakers. Lying prone across imaginary window ledge, head left looking toward viewer, chin resting on folded forearms, horizontal body and feet extending right. Restful breathing and blinking sequence eyes open, open, half closed, closed, half closed, open. Identical fixed body position and scale in all cells, ample margins all sides. No actual ledge, no window, no text, no grid, no shadow ground. Full body including hat and shoes in every cell. Wide transparent PNG.

Reference inputs were the respective original sheets; the silver result was also
used as a pose reference for the heart outfit. Outputs were 2172 × 724. Packaging
uses six 362-pixel columns, the common y=240..460 crop, a 184 × 112 resize, and
placement at (4, 78) in each runtime cell. No original sheet was edited.

These derived images are for local personal use under the existing artwork
license. This change does not grant permission to publicly redistribute modified
artwork; see `../LICENSE-ART.md`.
