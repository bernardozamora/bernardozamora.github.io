## WARNING ****
DO NOT rename the repository (bernardozamora.github.io) to something else.
This will break the website rendering.

## Website Architecture & Maintenance Guide

This repository powers [bernardozamora.com](https://bernardozamora.com) using **GitHub Pages**.

## High-Level Architecture

The website is a static site consisting entirely of HTML and assets, requiring no build steps, databases, or server-side code:
- **`index.html`**: Contains the complete structure, inline CSS styles, descriptive text, image plates, and the Brevo email subscription script.
- **`CNAME`**: A single-line configuration file containing `bernardozamora.com`, which instructs GitHub Pages to map the custom domain to this repository.
- **Image & Icon Assets**: High-resolution PNG files (e.g., `Image1_watermark.png`) and vector icons (`instagram.svg`, `pinterest.svg`) stored directly in the repository root and loaded relatively via `index.html`.

When you push changes to the `main` (or `master`) branch, GitHub Pages automatically publishes the root directory contents, serving them live to your custom domain via DNS records.

I'm using Brevo (brevo.com) to manage capturing emails (and later send some emails with the progress).

## How to Update the Website

### 1. Changing Text, Copy, or Descriptions
All text—including the main headline, introductory bio, upcoming book details, plate titles, and scientific explanations—lives directly inside `index.html`. 
* Open `index.html` in any text editor or GitHub's web editor.
* Locate the relevant text block (e.g., `<h1` for the title, `.tagline` for the bio, or `.plate-explanation` for image descriptions).
* Edit the text, save, and commit/push the file to update the live site.

### 2. Adding or Replacing Images (Plates)
To add a new mathematical visualization plate:
1. Export your optimized high-resolution image as a PNG and add it to the root of the repository.
2. In `index.html`, copy an existing `.plate` HTML block:
   ```html
   <div class="plate">
     <img src="YourNewImage_watermark.png" alt="Description of the image for accessibility">
     <div class="plate-caption">
       <span>Title of the Plate</span>
     </div>
     <p class="plate-explanation">Scientific or mathematical explanation of the visualization.</p>
   </div>
3. Paste the block into the .plates container section within index.html


## Styles
All design rules, colors (--ink, --paper, --accent, etc.), typography imports (Source Serif 4 and Inter), and responsive media queries are contained within the <style> block in the <head> of index.html. Modify these CSS variables or rules to alter the global aesthetic.
