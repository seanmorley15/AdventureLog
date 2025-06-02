# Installation with Haproxy

HAProxy is a free and open source software that provides a high availability load balancer and Proxy for TCP and HTTP-based applications.

You need to make the frontend and the backend available in order to have your AdventureLog working properly.
To do this, you will need to add 2 ACLs and 2 corresponding HAProxy backends in your haproxy configuration :
- One for your regular Adventurelog domain that will direct the requests to the frontend.
- One for the URLs that need to access the backend.

Example :

```
acl is_adventurelog hdr_sub(Host) -i adventurelog
acl is_adventurelog_backend path_beg /media/ or /admin/

use_backend adventurelog_media if is_adventurelog is_adventurelog_backend
use_backend adventurelog if is_adventurelog

backend alog
    server adventurelog 192.168.1.100:3000 check
backend adventurelog_backend
    server adventurelog_media 192.168.1.100:8000 check
```
