## General info

- Requires poetry

## ENV

Requires a `.env` file with the key:

```
OPENAI_API_KEY=sk-ABCDEF...
``` 

## RUN

run with `poetry run fastapi dev main.py`

## Flush memory

You can flush memory using the appropriate endpoint

```
curl -X DELETE http://127.0.0.1:8000/memory
```

## DATA
The raw data has been downloaded from:
https://github.com/SFOE/ichtankestrom_Documentation/blob/main/Access%20Download%20the%20data.md

