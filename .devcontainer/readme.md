If there is a need to move the .devcontainer into its own sub project, this will work! (after some alterations)

For instance when you need more than one .devcontainer (for other services).


## steps
1. Change the location of the main docker-compose file by adding `../` before the filepath:

    ```json
    // devcontainer.json
    ...
        "dockerComposeFile": [
        "../docker-compose.yml",
        "./docker-compose.dev.yml"
        ], 
    ...

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
2. The devcontainer cannot be run when other subprojects are present in the explorer. So you will need to open anew windown with only the subproject that you want to run the devcontainer in.

3. Thats is. You can now run the devcontainer as always.