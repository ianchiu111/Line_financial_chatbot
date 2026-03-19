
## debug
1. Issue: SSL certificate problem on Mac
    - reason: Mac Python can't verify SSL certificates when sending the reply back to LINE's API.
    - solution: Run this once in terminal:
        ```bash
        /Applications/Python\ 3.10/Install\ Certificates.command
        ```
