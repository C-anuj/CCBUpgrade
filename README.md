# CCBUpgrade

This script upgrades CocosBuilder 3 files to the SpriteBuilder 1.0 format.

## Installation

```
sudo pip install CCBUpgrade
```

## Usage

```
usage: ccbup.py [-h] [--destructive] project file [file ...]

positional arguments:
  project            A CocosBuilder CCB project file
  file               A CocosBuilder CCB file to process

optional arguments:
  -h, --help         show this help message and exit
  --destructive, -d  Modify files in-place.
```

## What it does

- Converts CCLayer to CCNode
- Converts CCLayerColor to CCNodeColor
- Converts CCLayerGradient to CCNodeGradient
- Converts CCMenu to CCNode
- Converts CCMenuItemImage to CCButton
- Converts CCParticleSystemQuad to CCParticleSystem
- Strips tags
- Renames displayFrame to spriteFrame
- Upgrades size, position, color, and opacity properties to the new format
- Fixes the callback and sound channels
- Removes the "ignoreAnchorPointForPosition" property and attempts to offset nodes to compensate (may or may not work)

## License
MIT
