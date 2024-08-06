#!/bin/bash

poetry run uvicorn app.app:app --host 0.0.0.0 --reload