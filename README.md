# kjandoc

> i needed something to combine multiple pptx files, i couldn't believe pandoc can't do that, so here's a creative but probably useless attempt at it.

## what it does
- merges multiple .pptx files into one
- preserves visual formatting by rendering slides and rebuilding a new deck
- pandoc-style usage: `kjandoc input1.pptx input2.pptx -o combined.pptx`

## why this exists
pandoc is great, but it can't concatenate powerpoint decks. 

this uses a headless libreoffice + pdf -> png rendering to get a pixel-perfect merge. 

the tradeoff is the output slides are images (not editable shapes).

## usage
```bash
# pandoc-style usage
./kjandoc input1.pptx input2.pptx -o combined.pptx

# tweak quality
./kjandoc input1.pptx input2.pptx -o combined.pptx --dpi 150
```

## deps
- python3
- libreoffice
- poppler (pdftoppm)
- python deps in requirements.txt

## notes
- output size is larger (images)
- visuals stay intact for the most part