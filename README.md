# BybitTradesHistory
Fetch bybit trades via websockets for one day in a Redis db

## Running
`docker compose up -d`


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
### redis setup
using a bit of https://geshan.com.np/blog/2022/01/redis-docker/



### TODO 
setup docker for dev and production:
- https://www.reddit.com/r/docker/comments/13kxfjf/how_to_handle_dockercompose_for_production_and/
