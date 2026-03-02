# kjandoc

> i needed something to combine multiple `.pptx` files, i couldn't believe `pandoc` can't do that, so here's a creative attempt at it using OOXML manipulation to do it.

https://github.com/user-attachments/assets/915940ab-f6a5-4e6f-b8dc-62de81d35c62

https://github.com/user-attachments/assets/c7fe58c1-ff76-41bf-977b-870247a6a3e2



## what it does
- merges multiple .pptx files into one
- preserves full editability, with 99% fidelity to the original formatting (some minor quirks may occur)
- copies slide masters, layouts, themes, notes, and embedded media
- `pandoc`-style usage: `kjandoc input1.pptx input2.pptx -o combined.pptx`

## why this exists
`pandoc` is great, but it can't concatenate `.pptx` files.

this works directly at the OOXML/ZIP level: it reads each `.pptx` as a ZIP archive, rewires all internal XML relationships, and writes a new near full Microsoft-compliant `.pptx`.

a final LibreOffice normalization pass cleans up any lingering structural quirks to prevent PowerPoint repair prompts (not guaranteed though).

## usage
```bash
# pandoc-style usage
./kjandoc input1.pptx input2.pptx -o combined.pptx

# merge more than two
./kjandoc a.pptx b.pptx c.pptx -o combined.pptx
```

## deps
- python3
- libreoffice (for the normalization pass)
- python deps in requirements.txt (`lxml`)

## notes
- output slides are fully editable
- masters and layouts from all source files are carried over
- duplicate media files are deduplicated automatically
