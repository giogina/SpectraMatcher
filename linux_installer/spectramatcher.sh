#!/bin/bash
if [ -z "$1" ]; then
    /opt/SpectraMatcher/SpectraMatcher
else
    # File passed — open mode
    /opt/SpectraMatcher/SpectraMatcher -open "$1"
fi

