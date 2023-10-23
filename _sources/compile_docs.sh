#!/bin/bash

make clean
make html
cp -r _build/html/* ../../protocol-gh-pages/
