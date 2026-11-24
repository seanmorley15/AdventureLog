# Invite a User

Admins can invite people by email. An invitation works even when [registration is disabled](../configuration/disable_registration.md), which makes it the way to add people to an invite-only server.

## Before you start

AdventureLog must be able to send email. See [SMTP Email](../configuration/email.md). Without it, the invitation is only written to the backend log.

## Send an invitation

1. Open the [Admin Panel](admin_panel.md).
2. Go to **Invitations → Invitations** and choose **Add**, or open `/admin/invitations/invitation/add/` directly.
3. Enter the person's email address and save. The invitation email is sent when you save.

## What the person does

They open the link in the email and create their account. They must sign up with the **same email address** the invitation went to. After signing up, they are a regular user; to make them an admin, see [Admin Panel](admin_panel.md#what-you-can-manage).
