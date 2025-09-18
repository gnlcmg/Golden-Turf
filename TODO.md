# Task: Fix UI Issues in Golden Turf App

## 1. Remove White Gap in Flipping Product List
- File: templates/products_list.html
- Issue: Potential white strip next to sidebar
- Fix: Ensure margin-left matches sidebar width (200px)
- Status: Check and fix if needed

## 2. Fix Contents Page with Bamboo and Pebbles
- File: templates/quotes.html
- Issue: Ensure bamboo and pebbles options are properly displayed
- Fix: Verify and adjust the other products section
- Status: Pending

## 3. Restore Sidebar in Client Details
- File: templates/clients.html
- Issue: Sidebar differs from quotes
- Fix: Make sidebar match quotes (width 200px, green, white text, bottom centered)
- Status: Pending

## 4. Ensure Consistent Sidebar Across All Pages
- Files: All template files (quotes, products_list, clients, invoice, dashboard, payments, calendar, etc.)
- Issue: Sidebars vary in width, color, bottom links
- Fix: Standardize to quotes style
- Status: Pending

## 5. Center Invoice Form Page
- File: templates/invoice.html
- Issue: Form touching sidebar or not centered
- Fix: Adjust margin-left and form centering
- Status: Pending

## Steps to Complete:
1. Update templates/clients.html sidebar to match quotes
2. Update templates/invoice.html sidebar and container margin
3. Check and update other templates for consistency
4. Verify products_list.html margin
5. Test and confirm all changes
