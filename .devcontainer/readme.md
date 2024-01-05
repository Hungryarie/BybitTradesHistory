# Multiple Dev containers
If there is a need for more than one devcontainer, for instance when you need more than one .devcontainer (for other services), you can move it into its own sub folder. There are some minor tweaks that you need to be aware off.

*Reference: https://www.youtube.com/watch?v=bVmczgfeR5Y* 

## Change the reference location of the main docker-compose file

1. Inside the .devcontainer, make a subfolder and place your `devcontainer.json` file + the rest (~ `docker-compose.dev.yml`) in that subfolder.  
2. Change the reference of the main docker-compose file by adding `../` before the filepath in the `devcontainer.json` file(s):
    
*before:*
```
.
+-- .devcontainer
|   +-- devcontainer.json
|   +-- (optionaly) docker-compose.dev.yml
```

```json
// devcontainer.json
...
    "dockerComposeFile": [
    "../docker-compose.yml",
    "./docker-compose.dev.yml"
    ], 
...
```
*after:*
```
.
+-- .devcontainer
|   +-- devcontainer1
|   |   +-- devcontainer.json
|   |   +-- (optionaly) docker-compose.dev.yml
```
```json
// devcontainer.json
...
    "dockerComposeFile": [
    "../../docker-compose.yml",
    "./docker-compose.dev.yml"
    ], 
...
```


## Thats is. 
You can now run/rebuild the devcontainer as always. VS code will promt you which container to rebuild/reopen