# Profile System Updates - TODO

## Changes to Implement:

### 1. Update User Registration Logic (app.py)
- [ ] Change `/register` route to always assign 'user' role to manually added users
- [ ] Only user ID 1 will be admin by default (first user)

### 2. Update Permission System (app.py)
- [ ] Modify `has_permission()` function to give admins automatic access to everything
- [ ] Update permission labels to be more specific:
  - `products_list` instead of `products`
  - `invoice` for invoice form
  - `clients` for client details form
  - `payments` for clients & invoices list
  - `calendar` for calendar
  - `dashboard` for dashboard
  - `profiles` for profiles
  - `quotes` for quotes

### 3. Update Templates
- [ ] Update `templates/profiles.html` - Change permission labels to match actual page names
- [ ] Update `templates/edit_user.html` - Update permission checkboxes to use new specific labels

### 4. Testing
- [ ] Test user registration (new users should be 'user' role)
- [ ] Test admin permissions (admins should have all access)
- [ ] Test permission assignment for regular users
- [ ] Verify all pages work with new permission labels
