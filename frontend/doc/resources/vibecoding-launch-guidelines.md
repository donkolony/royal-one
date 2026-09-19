# Vibecoding Launch Checklist
*A categorized reference compiled from social media "things to tell Claude" checklists*

---

## 1. Security

**Before launch:**
- Hide API keys
- Purge Git secrets (check git history for leaked secrets)
- Use environment variables for DB credentials (not a public/hardcoded key)
- Enable row-level security
- Encrypt sensitive data
- Enforce server-side auth
- Lock record access (per-user access control)
- Block field tampering (prevent client-side field manipulation)
- Secure session cookies
- Hash passwords (properly, with salt)
- Rate limit login attempts
- Add bot protection
- Parameterize database queries (prevent SQL injection)
- Validate all input
- Escape user content (prevent XSS)
- Restrict file upload types/size
- Trim/limit data in API responses (don't over-expose fields)
- Add security headers
- Force HTTPS
- Scan dependencies for vulnerabilities
- Update outdated dependencies
- Check environment variables aren't exposed
- Check for exposed files (`.env`, config files, etc.)
- Protect admin routes
- Secure API endpoints
- Check CORS settings
- Secure database access
- Turn off debug mode in production
- Do a full security audit before launch

---

## 2. Functionality & Bug Fixes

- Remove horizontal scroll issues
- Find and fix broken links
- Add a mobile navigation menu
- Add a favicon
- Fix page titles
- Add meta descriptions
- Fix footer links
- Add a custom 404 page
- Update copyright year (dynamic, not hardcoded)
- Compress images
- Fix broken buttons
- Add success messages (form/action feedback)
- Add error messages
- Remove leftover placeholder text
- Remove unused nav items
- Fix mobile overflow issues
- Make logo clickable (links home)
- Make phone number clickable (`tel:` link)
- Make email clickable (`mailto:` link)
- Fully optimize for mobile

---

## 3. Legal & Compliance

- Add a Privacy Policy page
- Add Terms & Conditions page
- Add a Refund Policy
- Add a Cookies Policy
- Add a cookie consent banner
- Add form consent checkboxes where needed
- Check local laws/regulations for your business/region
- Add real, verifiable business details (not placeholder info)
- Only collect data you actually need
- Remove fake reviews
- Remove fake/unsupported metrics or claims
- Check copyright status of images used
- Check third-party embeds for compliance
- Check tracking/analytics compliance (consent, disclosures)
- Remove "Made with AI" tags if not desired/required

---

## 4. Accessibility

- Check color contrast ratios
- Add alt text to all images
- Fix general accessibility issues (ARIA labels, semantic HTML)
- Use clear, descriptive button labels
- Make forms keyboard-friendly (tab order, focus states)

---

## 5. SEO & Technical Setup

- Add internal links between pages
- Connect a custom domain
- Add meta descriptions per page
- Add a custom 404 page
- Add breadcrumbs
- Add alt text on images
- Clean up page source/markup
- Use unique headings (H1/H2) per page
- Add canonical tags
- Add structured data (schema.org)
- Use unique page titles per page
- Fix browser console errors
- Remove production source maps
- Add an `llms.txt` file
- Add a `robots.txt` file
- Add local business schema (for local SEO)
- Add a favicon
- Add a `sitemap.xml`
- Add social share images (Open Graph/Twitter cards)
- Reduce oversized JS bundles

---

## 6. Design — Signs Your App "Looks Vibecoded" (Avoid These)

- Purple-to-blue gradient (overused default)
- Gradient hero text
- Emojis inside headings
- Inter font used everywhere (default, no distinct typography)
- Colored border cards
- Glassmorphism cards
- Low-contrast dark mode
- Three icon boxes in a row (generic feature layout)
- Badge sitting above the headline
- Lucide icons used everywhere by default
- Untouched/default shadcn UI components
- Fade-in animations on scroll (overused)
- Cursor-following beam/glow effect
- Buttons that fade on hover (generic)
- Inconsistent spacing
- Em dashes used everywhere in copy
- Generic buzzword copy
- Serif italic accents
- Space Grotesk + Instrument Serif font pairing (overused combo)
- Grain texture over a gradient

**Additional quick "do/don't" pass:**
| ❌ Avoid | ✅ Do |
|---|---|
| Purple gradient | Custom favicon |
| Vague hero text | Privacy policy page |
| Fake reviews | Custom domain |
| Too much scroll animation | |
| Pill-shaped buttons (overused) | |
| Emoji icons | |
| Fake metrics | |
| Em dashes | |
| "Made with AI" tag | |

---

## 7. UX Features Worth Adding

- Dark mode toggle
- Simple cookie consent banner
- Site search
- "Back to top" button
- Mobile menu
- Loading animations
- Hover states
- Scroll progress bar
- Copy-to-clipboard button
- Print stylesheet
- Sticky headers
- "Skip to content" link
- Password visibility toggle
- UTM tracking on links
- Form success state
- Form error state
- Confirmation modals
- "Last updated" date display
- Expandable FAQ section
- Floating contact button

---

## 8. Files to Prepare Before Vibecoding an App

1. **PRD** (Product Requirements Document)
2. **ARCHITECTURE.md**
3. **ARCHITECTURE-ESSENTIALS.md**
4. **AGENTS.md**
5. **CLAUDE.md**
6. *(a 6th file was referenced but cut off in the source — likely a README.md or similar setup doc)*

---

*Compiled from short-form video checklists (@millee.md, @yatesvids, @andov.zip). Use as a working reference — not all items apply to every project (e.g., a public DB key may be intentional for certain read-only use cases).*
