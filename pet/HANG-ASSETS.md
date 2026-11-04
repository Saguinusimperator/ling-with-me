# Hanging animation assets

`ling/hang.png` and `ling-heart/hang.png` are standalone Windows app assets.
Original sprite sheets, Pets manifests, and resting strips are preserved.
Each strip has eight transparent 192 × 208 cells. Frame duration is 250 ms,
giving a two-second loop. Silver grips are registered to (74, 10) and (118, 10).
The heart outfit uses equal horizontal/vertical scaling of 0.46 to preserve its
original proportions, with grips approximately (79.44, 10) and (112.56, 10).
Both outfits use the midpoint (96, 10) as the window attachment anchor.

Both atlases were generated with the built-in imagegen tool on 2026-11-04.
The silver reference was `ling/spritesheet.webp`; the heart references were
`ling-heart/spritesheet.webp` and the generated silver hanging atlas. Generated
sources remain locally under `build/hanging-qa/source/`. They are 1254 × 1254,
arranged as four columns and two rows. `tools/pack_hanging.py` slices, registers,
and resizes these frames; `build/hanging-qa/registration.json` records the mapping.
Packaging aligns grip midpoints and their shared height;
the body motion itself comes from imagegen, not rotating the whole character.

## Silver prompt

Generate a transparent sprite animation atlas of the EXACT blond chibi silver futuristic jumpsuit character in reference. ACTION: hanging from an invisible overhead ledge, TWO arms fully raised above head, both hands gripping invisible edge at identical fixed positions in EVERY frame, body hanging below hands, feet dangling. No actual bar or ledge drawn. Exactly EIGHT frames in a precise 4 columns by 2 rows grid of equal square cells (reading order left to right then next row). Full figure and both hands contained with margins in each cell. Constant camera, character identity, size, detailed soft illustrated sticker style. A gentle pendulum: frame1 body centered; frame2 legs slightly left; frame3 legs leftmost (~8 degrees); frame4 legs slightly left; frame5 center, blinking; frame6 legs slightly right; frame7 rightmost (~8 degrees); frame8 slightly right. Hands must remain at same two anchor points above head at cell x=40% and 60%, y=10%; arms flex to keep grips stationary, only torso and legs sway, never move whole figure side to side. Blond hair, silver suit and boots match reference. Transparent background, no text, no numbers, no grid lines, no ground, no shadows, no props, no extra limbs. Output square atlas.

## Heart prompt

Make an EIGHT-frame transparent sprite atlas in exact 4 columns x 2 rows equal cells. Use the EXACT blond chibi character/outfit in reference1: WHITE round hat with narrow dark band, white shirt, red necktie, navy shorts with red hearts, red sneakers. Use pose sequence and fixed hand positions from reference2. Both arms raised overhead, BOTH hands grip an invisible horizontal ledge above head. Head/body/feet all BELOW the hands; hat stays on head. Hanging like on a pull-up bar, with gentle pendulum sway, NO jumping. Keep both hands at identical coordinates within each cell throughout all eight frames; body and legs below hands sway left then right: centered, slight left, leftmost 8degrees, slight left, center blinking, slight right, rightmost 8degrees, slight right. Same scale, same camera, full body/hands/shoes inside each cell with margins. Match detailed soft illustration sticker style of references. Transparent background, NO bar drawn, no window, no props, no lettering, no numbers, no gridlines, no ground shadows. Output square atlas.

These derived images remain subject to the artwork restrictions in
`../LICENSE-ART.md`; generating local assets does not grant permission to
redistribute modified artwork.
