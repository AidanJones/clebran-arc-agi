#!/bin/sh
# Fetch external dependencies (not committed; vendored DSL lives in clebran/dsl/_vendor)
git clone --depth 1 https://github.com/michaelhodel/arc-dsl third_party/arc-dsl
git clone --depth 1 https://github.com/fchollet/ARC-AGI third_party/ARC-AGI
