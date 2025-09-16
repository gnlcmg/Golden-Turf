# TODO: Implement Modules Access Control

## Pending Tasks
- [ ] Add helper functions in app.py for admin constraints (check admin count, prevent self-role change)
- [ ] Update edit_user POST route to enforce role change restrictions
- [ ] Update edit_user.html to disable role change for own user and add info text
- [ ] Update profiles route if needed to handle restrictions
- [ ] Test access control for various scenarios (user id=1, single admin, self-edit)
