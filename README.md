Requires poetry.

##ENV

Requires a `.env` file with the key:

```
OPENAI_API_KEY=sk-ABCDEF...
``` 

##RUN

run with `poetry run fastapi dev main.py`

##Flush memory

You can flush memory using the appropriate endpoint

```
curl -X DELETE http://127.0.0.1:8000/memory
```


