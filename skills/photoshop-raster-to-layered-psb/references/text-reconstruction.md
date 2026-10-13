# Editable text reconstruction

## Detection

Use a high-quality OCR engine that returns line polygons, recognized text, confidence, per-character boxes, and character tokens. A downscaled preview can improve layout-wide detection when the source is extremely large, provided coordinates are scaled independently in X and Y back to the original canvas.

Split merged OCR lines when character-center spacing shows a clear semantic gap. Correct OCR text only when the source or authoritative document meaning supports the correction; retain the raw OCR value in the manifest.

## Full local font scan

Enumerate readable TTF, OTF, TTC, and OTC faces from system, user, and application font directories. TTC and OTC files require a face index. Record PostScript name, family, style, file path, face index, and task-character coverage.

For each text item:

1. Skip fonts that lack required characters.
2. Render the recognized string and crop to the glyph mask.
3. Normalize the candidate and source crop for size while retaining stroke and contour differences.
4. Compare blurred binary or grayscale masks.
5. Keep the best and runner-up, raw errors, and their relative gap.
6. Apply a semantic filter for numbers and Latin text so symbol fonts cannot win solely through an accidental glyph mapping.

A large candidate set improves recall but also increases false coincidences. Font-family selection, semantic plausibility, Photoshop availability, and glyph error must agree.

## Style estimation

- Point size: desired glyph pixel height divided by the candidate font glyph-height ratio, multiplied by 72 and divided by document DPI.
- Horizontal scale: observed character or line width divided by the rendered width. Respect the precision supported by the target Photoshop version.
- Tracking: after horizontal scale is fixed, distribute the remaining line-width difference across character gaps and convert it to thousandths of an em.
- Weight: prefer an actual regular, medium, semibold, or bold face. Use faux bold only when no suitable real face exists and measured stroke width supports it.
- Color: estimate the foreground cluster inside the text polygon. Lower confidence on textured maps, outlines, shadows, gradients, or colored symbols.
- Position: write point text, then compare Photoshop layer bounds to the target OCR box and translate the text position. Iterate size and width only within bounded tolerances.

## Confidence and completion

OCR confidence and font-fit confidence measure different things. High OCR confidence does not prove the font, and a close font match does not prove the recognized text.

The manifest should include raw OCR text, corrected text, OCR confidence, font and runner-up, font-fit error and confidence gap, size, horizontal and vertical scale, tracking, weight, color, point position, target box, Photoshop-rendered bounds, and correction status.

Accept the structural text result only after save and reopen confirm every intended layer is still a Photoshop text layer. Preserve a source-pixel text reference and make uncertain items easy to find.
