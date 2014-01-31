#!/usr/bin/env python

import plistlib
import argparse
import logging
import copy
import os

try:
	import dimensions
except ImportError:
	logging.critical('Please install the \'dimensions\' Python package: sudo pip install dimensions')
	exit(1)

kCCBSizeTypeAbsolute = 0
kCCBSizeTypePercent = 1
kCCBSizeTypeRelativeContainer = 2
kCCBSizeTypeHorizontalPercent = 3
kCCBSizeTypeVerticalPercent = 4
kCCBSizeTypeMultiplyResolution = 5

CCSizeUnitPoints = 0
CCSizeUnitUIPoints = 1
CCSizeUnitNormalized = 2
CCSizeUnitInsetPoints = 3
CCSizeUnitInsetUIPoints = 4

# Figure out the absolute position of a node from the bottom left
def absolutePosition(node, parentSize):
	positionProp = None
	for prop in node['properties']:
		if prop['type'] == 'Position':
			positionProp = prop
			break

	if positionProp is None:
		return [0, 0]

	pt = positionProp['value']
	posType = pt[2]

	absPt = [0, 0]

	if posType == kCCBPositionTypeRelativeBottomLeft or posType == kCCBPositionTypeMultiplyResolution:
		absPt = pt
	elif posType == kCCBPositionTypeRelativeTopLeft:
		absPt[0] = pt[0]
		absPt[1] = parentSize[1] - pt[1]
	elif posType == kCCBPositionTypeRelativeTopRight:
		absPt[0] = parentSize[0] - pt[0]
		absPt[1] = parentSize[1] - pt[1]
	elif posType == kCCBPositionTypeRelativeBottomRight:
		absPt[0] = parentSize[0] - pt[0]
		absPt[1] = pt[1]
	elif posType == kCCBPositionTypePercent:
		absPt[0] = int(parentSize[0] * pt[0] / 100.0)
		absPt[1] = int(parentSize[1] * pt[1] / 100.0)
	
	return absPt

# Try to offset the absolute position of a node. This may or may not work.
def offsetAbsolutePosition(positionProp, parentSize, offset):
	posType = positionProp['value'][2]

	pos = [positionProp['value'][0] + offset[0], positionProp['value'][1] + offset[1]]

	finalPos = [0, 0]

	if posType == kCCBPositionTypeRelativeBottomLeft or posType == kCCBPositionTypeMultiplyResolution:
		finalPos = pos
	elif posType == kCCBPositionTypeRelativeTopLeft:
		finalPos[0] = pos[0]
		finalPos[1] = parentSize[1] - pos[1]
	elif posType == kCCBPositionTypeRelativeTopRight:
		finalPos[0] = parentSize[0] - pos[0]
		finalPos[1] = parentSize[1] - pos[1]
	elif posType == kCCBPositionTypeRelativeBottomRight:
		finalPos[0] = parentSize[0] - pos[0]
		finalPos[1] = pos[1]
	elif posType == kCCBPositionTypePercent:
		if parentSize[0] == 0:
			finalPos[0] = pos[0]
		else:
			finalPos[0] = pos[0] * 100.0 / parentSize[0]
		if parentSize[1] == 0:
			finalPos[1] = pos[1]
		else:
			finalPos[1] = pos[1] * 100.0 / parentSize[1]

	positionProp['value'][0] = finalPos[0]
	positionProp['value'][1] = finalPos[1]

# Convert CCLayer to CCNode
# Convert CCLayerColor to CCNodeColor
# Convert CCLayerGradient to CCNodeGradient
# Remove deprecated properties
def stripCCLayer(node):
	isColorLayer = node['baseClass'] == 'CCLayerColor'
	isGradientLayer = node['baseClass'] == 'CCLayerGradient'
	if node['baseClass'] == 'CCLayer' or isColorLayer or isGradientLayer:
		if isColorLayer:
			node['baseClass'] = 'CCNodeColor'
		elif isGradientLayer:
			node['baseClass'] = 'CCNodeGradient'
		else:
			node['baseClass'] = 'CCNode'
		
	# Strip invalid properties
	stripProps = ['touchEnabled', 'mouseEnabled']
	props = node['properties']
	for prop in list(props):
		if prop['name'] in stripProps:
			props.remove(prop)

# Remove tag property
def stripTag(node):
	props = node['properties']
	for prop in list(props):
		if prop['name'] == 'tag':
			props.remove(prop)

# Calculate the size of an image reference
def imageSize(project, imagePath):
	for resourcePath in project['resourcePaths']:
		path = os.path.join(project['location'], resourcePath['path'])

		finalPath = os.path.join(path, imagePath)
		if os.path.isfile(finalPath):
			return list(dimensions.dimensions(finalPath))[:2]

		basename = os.path.basename(imagePath)
		dirname = os.path.dirname(imagePath)

		finalPath = os.path.join(path, dirname, 'resources-auto', basename)
		if os.path.isfile(finalPath):
			d = dimensions.dimensions(finalPath)
			return [int(d[0] * 0.25), int(d[1] * 0.25)]

		finalPath = os.path.join(path, basename, 'resources-iphone', basename)
		if os.path.isfile(finalPath):
			return list(dimensions.dimensions(finalPath))[:2]

	logging.warning('Failed to determine size of image \'%s\'' % imagePath)
	return [0, 0]

# Convert CCMenu to CCNode
# Convert CCMenuItemImage to CCButton
def convertCCMenu(project, node):
	if node['baseClass'] == 'CCMenu':
		node['baseClass'] = 'CCNode'
	
	if node['baseClass'] == 'CCMenuItemImage':
		node['baseClass'] = 'CCButton'
		normalSpriteFrame = None
		for prop in node['properties']:
			if prop['name'] == 'normalSpriteFrame':
				prop['name'] = 'backgroundSpriteFrame|Normal'
				normalSpriteFrame = prop
			if prop['name'] == 'selectedSpriteFrame':
				prop['name'] = 'backgroundSpriteFrame|Highlighted'
			if prop['name'] == 'disabledSpriteFrame':
				prop['name'] = 'backgroundSpriteFrame|Disabled'
			if prop['name'] == 'isEnabled':
				prop['name'] = 'userInteractionEnabled'

		node['properties'].append({
			'name': 'title',
			'type': 'String',
			'value': '',
		})

		if normalSpriteFrame is not None:
			selectedSpriteFrame = copy.deepcopy(normalSpriteFrame)
			selectedSpriteFrame['name'] = 'backgroundSpriteFrame|Selected'
			node['properties'].append(selectedSpriteFrame)

			size = imageSize(project, normalSpriteFrame['value'][1])
			node['properties'].append({
				'name': 'preferredSize',
				'type': 'Size',
				'value': [
					size[0],
					size[1],
					0,
					0,
				],
			})

# Set the type of a sequence channel and all its keyframes
def setChannelType(channel, code):
	channel['type'] = code
	for keyframe in channel['keyframes']:
		keyframe['type'] = code

# Change callbackChannel type to 12
# Change soundChannel type to 11
def convertCallbacks(root):
	for sequence in root['sequences']:
		setChannelType(sequence['callbackChannel'], 12)
		setChannelType(sequence['soundChannel'], 11)

# Convert opacity from (0-255) range to (0-1) range
# Change opacity keyframe type to 10
def convertOpacity(node):
	for prop in node['properties']:
		if prop['name'] == 'opacity':
			prop['type'] = 'Float'
			prop['value'] /= 255.0

			value = prop.get('baseValue')
			if value is not None:
				prop['baseValue'] = value / 255.0
	
	if 'animatedProperties' in node:
		for index, prop in node['animatedProperties'].iteritems():
			if 'opacity' in prop:
				prop['opacity']['type'] = 10
				for keyframe in prop['opacity']['keyframes']:
					keyframe['value'] /= 255.0
					keyframe['type'] = 10

# Convert CCParticleSystemQuad to CCParticleSystem
def convertParticleSystem(node):
	if node['baseClass'] == 'CCParticleSystemQuad':
		node['baseClass'] = 'CCParticleSystem'

# Remove ignoreAnchorPointForPosition property and attempt to offset the node to compensate
def convertAndStripIgnoreAnchorPointForPosition(parent, parentSize, absSize, node):
	props = node['properties']
	convert = False
	anchorProperty = None
	positionProperty = None
	for prop in list(props):
		if prop['type'] == 'Position':
			positionProperty = prop
		if prop['name'] == 'ignoreAnchorPointForPosition':
			props.remove(prop)
			convert = convert or prop['value']
		if prop['name'] == 'anchorPoint':
			anchorProperty = prop
	
	if parent is None:
		anchorProperty['value'] = [0, 0]
	
	if positionProperty is None and 'animatedProperties' in node:
		# No position property. That means it's animated. Oh no.
		for index, prop in node['animatedProperties'].iteritems():
			if 'position' in prop:
				positionProperty = prop['position']
				break
	
	if positionProperty is not None and convert:
		offset = [anchorProperty['value'][0] * absSize[0], anchorProperty['value'][1] * absSize[1]]
		if 'keyframes' in positionProperty:
			for keyframe in positionProperty['keyframes']:
				offsetAbsolutePosition(keyframe, parentSize, offset)
		else:
			offsetAbsolutePosition(positionProperty, parentSize, offset)

CCPositionUnitPoints = 0
CCPositionUnitUIPoints = 1
CCPositionUnitNormalized = 2

CCPositionReferenceCornerBottomLeft = 0
CCPositionReferenceCornerTopLeft = 1
CCPositionReferenceCornerTopRight = 2
CCPositionReferenceCornerBottomRight = 3

kCCBPositionTypeRelativeBottomLeft = 0
kCCBPositionTypeRelativeTopLeft = 1
kCCBPositionTypeRelativeTopRight = 2
kCCBPositionTypeRelativeBottomRight = 3
kCCBPositionTypePercent = 4
kCCBPositionTypeMultiplyResolution = 5

# Convert to new position format
# Convert percentage values from (0-100) range to (0-1) range
def convertPosition(node):
	posType = -1
	positionProp = None
	for prop in node['properties']:
		if prop['type'] == 'Position':
			value = prop['value']
			if len(value) < 5:
				posType = value[2]

				while len(value) < 5:
					value.append(0)

				if posType == kCCBPositionTypeRelativeBottomLeft:
					value[2] = CCPositionReferenceCornerBottomLeft
					value[3] = value[4] = CCPositionUnitPoints
				elif posType == kCCBPositionTypeMultiplyResolution:
					value[2] = CCPositionReferenceCornerBottomLeft
					value[3] = value[4] = CCPositionUnitUIPoints
				elif posType == kCCBPositionTypeRelativeTopLeft:
					value[2] = CCPositionReferenceCornerTopLeft
					value[3] = value[4] = CCPositionUnitPoints
				elif posType == kCCBPositionTypeRelativeTopRight:
					value[2] = CCPositionReferenceCornerTopRight
					value[3] = value[4] = CCPositionUnitPoints
				elif posType == kCCBPositionTypeRelativeBottomRight:
					value[2] = CCPositionReferenceCornerBottomRight
					value[3] = value[4] = CCPositionUnitPoints
				elif posType == kCCBPositionTypePercent:
					value[0] /= 100.0
					value[1] /= 100.0
					value[2] = CCPositionReferenceCornerBottomLeft
					value[3] = value[4] = CCPositionUnitNormalized
				positionProp = prop
				break
	
	if posType == kCCBPositionTypePercent:
		if 'animatedProperties' in node:
			for index, prop in node['animatedProperties'].iteritems():
				if 'position' in prop:
					if positionProp is not None:
						positionProp['baseValue'] = copy.deepcopy(positionProp['value'])
					for keyframe in prop['position']['keyframes']:
						keyframe['value'][0] /= 100.0
						keyframe['value'][1] /= 100.0

# Change displayFrame property to spriteFrame
def convertSpriteFrames(node):
	spriteFrameProp = None
	for prop in node['properties']:
		if prop['name'] == 'displayFrame':
			prop['name'] = 'spriteFrame'
			spriteFrameProp = prop
			break
	
	if 'animatedProperties' in node:
		if spriteFrameProp is not None:
			spriteFrameProp['baseValue'] = [
				spriteFrameProp['value'][1],
				'Use regular file',
			]
		for index, prop in node['animatedProperties'].iteritems():
			if 'displayFrame' in prop:
				displayFrame = prop['displayFrame']
				del prop['displayFrame']
				prop['spriteFrame'] = displayFrame
				for keyframe in prop['spriteFrame']['keyframes']:
					keyframe['name'] = 'spriteFrame'

# Convert to new size format
def convertSize(node):
	for prop in node['properties']:
		if prop['type'] == 'Size':
			value = prop['value']

			if value[2] == kCCBSizeTypeAbsolute:
				value[2] = CCSizeUnitUIPoints
				if len(value) < 4:
					value.append(CCSizeUnitUIPoints)
				else:
					value[3] = CCSizeUnitUIPoints

			elif value[2] == kCCBSizeTypePercent:
				value[0] /= 100.0
				value[1] /= 100.0
				value[2] = CCSizeUnitNormalized
				if len(value) < 4:
					value.append(CCSizeUnitNormalized)
				else:
					value[3] = CCSizeUnitNormalized

			elif value[2] == kCCBSizeTypeRelativeContainer:
				value[2] = CCSizeUnitInsetUIPoints
				if len(value) < 4:
					value.append(CCSizeUnitInsetUIPoints)
				else:
					value[3] = CCSizeUnitInsetUIPoints

			elif value[2] == kCCBSizeTypeHorizontalPercent:
				value[0] /= 100.0
				value[2] = CCSizeUnitNormalized
				if len(value) < 4:
					value.append(CCSizeUnitUIPoints)
				else:
					value[3] = CCSizeUnitUIPoints

			elif value[2] == kCCBSizeTypeVerticalPercent:
				value[1] /= 100.0
				value[2] = CCSizeUnitUIPoints
				if len(value) < 4:
					value.append(CCSizeUnitNormalized)
				else:
					value[3] = CCSizeUnitNormalized

			elif value[2] == kCCBSizeTypeMultiplyResolution:
				value[2] = CCSizeUnitPoints
				if len(value) < 4:
					value.append(CCSizeUnitPoints)
				else:
					value[3] = CCSizeUnitPoints

# Convert RGB values from (0-255) range to (0-1) range
def convertColor3(node):
	for prop in node['properties']:
		if prop['type'] == 'Color3':
			value = prop['value']
			for i in xrange(len(value)):
				value[i] /= 255.0
			while len(value) < 4:
				value.append(1)

			value = prop.get('baseValue')
			if value is not None:
				for i in xrange(len(value)):
					value[i] /= 255.0
				while len(value) < 4:
					value.append(1)
	
	if 'animatedProperties' in node:
		for index, prop in node['animatedProperties'].iteritems():
			if 'color' in prop:
				for keyframe in prop['color']['keyframes']:
					value = keyframe['value']
					for i in xrange(len(value)):
						value[i] /= 255.0
					while len(value) < 4:
						value.append(1)

# Calculate absolute size of a node
def absoluteSize(project, node, parentSize):
	sizeProp = None
	for prop in node['properties']:
		if prop['name'] == 'contentSize':
			sizeProp = prop
			break

	if sizeProp is None:
		for prop in node['properties']:
			if prop['type'] == 'SpriteFrame':
				return imageSize(project, prop['value'][1])

		return [0, 0]
	
	absSize = [0, 0]
	size = sizeProp['value']
	sizeType = sizeProp['value'][2]
	if sizeType == kCCBSizeTypeAbsolute or sizeType == kCCBSizeTypeMultiplyResolution:
		absSize = size[:2]
	elif sizeType == kCCBSizeTypeRelativeContainer:
		absSize[0] = parentSize[0] - size[0]
		absSize[1] = parentSize[1] - size[1]
	elif sizeType == kCCBSizeTypePercent:
		absSize[0] = int(parentSize[0] * size[0] / 100.0)
		absSize[1] = int(parentSize[1] * size[1] / 100.0)
	elif sizeType == kCCBSizeTypeHorizontalPercent:
		absSize[0] = int(parentSize[0] * size[0] / 100.0)
		absSize[1] = size[1]
	elif sizeType == kCCBSizeTypeVerticalPercent:
		absSize[0] = size[0]
		absSize[2] = int(parentSize[1] * size[1] / 100.0)
	
	return absSize

# Build a new path to write to in case we are doing this non-destructively
def nonDestructivePath(f):
	fileNameParts = os.path.splitext(f)
	return fileNameParts[0] + '-new' + fileNameParts[1]

# Fix CCBFile references if we are doing this non-destructively
def fixCCBPaths(node):
	for prop in node['properties']:
		if prop['type'] == 'CCBFile':
			prop['value'] = nonDestructivePath(prop['value'])

trace = []

# Process a CCNode
def process(project, parent, parentSize, node, args):
	try:
		absSize = absoluteSize(project, node, parentSize)

		convertSize(node)

		stripCCLayer(node)

		stripTag(node)

		convertCCMenu(project, node)

		convertParticleSystem(node)

		convertAndStripIgnoreAnchorPointForPosition(parent, parentSize, absSize, node)

		if not args.destructive:
			fixCCBPaths(node)

		convertSpriteFrames(node)

		convertPosition(node)

		convertColor3(node)

		convertOpacity(node)

		for child in node['children']:
			process(project, node, absSize, child, args)

	except Exception:
		klass = node.get('customClass')
		if klass is None or klass == '':
			klass = node.get('baseClass')
		error = '> "%s" of type %s' % (node.get('displayName'), klass)
		if parent is None:
			logging.critical('Node hierarchy:\n' + ', parent of\n'.join(reversed(trace)))
		else:
			trace.append(error)
		raise

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description = 'Converts CocosBuilder 3 files to the SpriteBuilder 1.0 format.' +
			' Visit https://github.com/sidebolt/CCBUpgrade for more info.')
	parser.add_argument('project', metavar = 'project', type = str, help = 'A CocosBuilder CCB project file')
	parser.add_argument('files', metavar = 'file', type = str, nargs='+', help = 'A CocosBuilder CCB file to process')
	parser.add_argument('--destructive', '-d', dest = 'destructive', action = 'store_true', default = False, help = 'Modify files in-place.')
	args = parser.parse_args()

	logging.basicConfig(level = logging.DEBUG)

	project = plistlib.readPlist(args.project)
	project['location'] = os.path.abspath(os.path.dirname(args.project))

	for f in args.files:
		logging.info('Processing %s...' % f)
		doc = plistlib.readPlist(f)
		
		convertCallbacks(doc)

		process(project, None, [480, 320], doc['nodeGraph'], args)

		if args.destructive:
			newFile = f
		else:
			newFile = nonDestructivePath(f)

		plistlib.writePlist(doc, newFile)

		logging.info('Wrote %s' % newFile)
