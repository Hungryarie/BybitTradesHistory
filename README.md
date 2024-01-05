# BybitTradesHistory
Fetch bybit trades via websockets for one day in a Redis db

## Production
after debugging rebuild the container with: 
`docker compose up --build`  
otherwise just run:
`docker compose up -d`

## Developing
(VSCODE specific)  
`ctrl-shift-p` to open the command palette.  
type/click `Dev Containers: Rebuild and Reopen in Container`   
or *without*  rebuild use `Dev Containers: Reopen in Container`
a new windonw should open inside the container with the the workdir of the FastApi code (volume mount of => api/app/)  

since the Dockerfile.dev has an entrypoint set that waits for the attachment of the debugger, you should attach to it by utilizing the `Python: Remote Attach` launch config. See example below:

```json
// lauch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Remote Attach",
            "type": "python",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5678
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "."
                }
            ],
            "justMyCode": true
        }
    ]
}
```

for json reference on devcontainers: https://containers.dev/implementors/json_reference/

### devcontainer errors
try to rebuild the devcontainer(s)!

## troubleshooting

### fix error in redis container
this error will show when you run `docker compose up` command:
```bash
redis  | 1:C 31 Dec 2023 07:26:06.468 # WARNING Memory overcommit must be enabled! Without it, a background save or replication may fail under low memory condition. Being disabled, it can also cause failures without low memory condition, see https://github.com/jemalloc/jemalloc/issues/1328. To fix this issue add 'vm.overcommit_memory = 1' to /etc/sysctl.conf and then reboot or run the command 'sysctl vm.overcommit_memory=1' for this to take effect.
```


**run on your host machine** (has nothing to do with the redis image)  
ref: https://medium.com/@akhshyganesh/redis-enabling-memory-overcommit-is-a-crucial-configuration-68dbb77dae5f

run: `sudo nano /etc/sysctl.conf`
add at the end of this file the following line:  
`vm.overcommit_memory = 1`
save and exit ctrl-s ctrl-x

apply config by: `sudo sysctl -p`

redis should now run without this error!

## References
### Redis setup
using a bit of https://geshan.com.np/blog/2022/01/redis-docker/
### Depends on, links, networks
- https://www.baeldung.com/ops/docker-compose-links-depends-on


### TODO 
setup docker for dev and production:
- https://www.reddit.com/r/docker/comments/13kxfjf/how_to_handle_dockercompose_for_production_and/
- https://toptechtips.github.io/2023-05-17-docker-compose-multiple-dev-containers/