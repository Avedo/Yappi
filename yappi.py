#!/usr/bin/env python
import sys, os, codecs, re
from lxml import etree

# Coarse hack for coercing input to utf-8.
reload(sys)
sys.setdefaultencoding('utf_8')

sys.path.append('/usr/share/inkscape/extensions')
import inkex
from simplestyle import *
from copy import deepcopy

def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

class Stack(list):
    def push(self, item):
        self.append(item)

    def peek(self):
        return self[-1]

    def isEmpty(self):
        return not self

class Yappi(inkex.Effect):
    LogoStyle = enum('CROP', 'FIT_PARENT')

    SODIPODI = 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd'
    CC = 'http://creativecommons.org/ns#'
    CCOLD = 'http://web.resource.org/cc/'
    SVG = 'http://www.w3.org/2000/svg'
    DC = 'http://purl.org/dc/elements/1.1/'
    RDF = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
    INKSCAPE = 'http://www.inkscape.org/namespaces/inkscape'
    XLINK = 'http://www.w3.org/1999/xlink'
    XML = 'http://www.w3.org/XML/1998/namespace'

    def __init__(self):
        # Call the base class constructor.
        inkex.Effect.__init__(self)

        # Fetch the users' home directory ...
        homeDir = os.path.expanduser('~')
        
        # ... and setup the path to the log file.
        self.logFile = os.path.join(homeDir, 'yappi.log')

        # Definition of script parameters (Ensure that the second parameter matches the names in the inx file).
        self.OptionParser.add_option('--textColor', action='store', type='string', dest='textColor', help='Color of normal text')
        self.OptionParser.add_option('--titleColor', action='store', type='string', dest='titleColor', help='Color of the title')
        self.OptionParser.add_option('--titleBgColor', action='store', type='string', dest='titleBgColor', help='The title background color')
        self.OptionParser.add_option('--hintColor', action='store', type='string', dest='hintColor', help='Color of the hint')
        self.OptionParser.add_option('--hintBgColor', action='store', type='string', dest='hintBgColor', help='The hint background color')
        self.OptionParser.add_option('--mainBgColor', action='store', type='string', dest='mainBgColor', help='The main background color')
        self.OptionParser.add_option('--borderColor', action='store', type='string', dest='borderColor', help='Color of the basic shape')

        self.OptionParser.add_option('--logoPath', action='store', type='string', dest='logoPath', help='Path to the main logo')
        self.OptionParser.add_option('--logoBgColor', action='store', type='string', dest='logoBgColor', help='The logo side background color')

        self.OptionParser.add_option('--sideOneText', action='store', type='string', dest='sideOneText', help='Subhead text')
        self.OptionParser.add_option('--sideOneHint', action='store', type='string', dest='sideOneHint', help='Subhead hint')
        self.OptionParser.add_option('--sideOneIcon', action='store', type='string', dest='sideOneIcon', help='Subhead icon')

        self.OptionParser.add_option('--sideTwoText', action='store', type='string', dest='sideTwoText', help='Subhead text')
        self.OptionParser.add_option('--sideTwoHint', action='store', type='string', dest='sideTwoHint', help='Subhead hint')
        self.OptionParser.add_option('--sideTwoIcon', action='store', type='string', dest='sideTwoIcon', help='Subhead icon')

        self.OptionParser.add_option('--sideThreeText', action='store', type='string', dest='sideThreeText', help='Subhead text')
        self.OptionParser.add_option('--sideThreeHint', action='store', type='string', dest='sideThreeHint', help='Subhead hint')
        self.OptionParser.add_option('--sideThreeIcon', action='store', type='string', dest='sideThreeIcon', help='Subhead icon')

        self.OptionParser.add_option('--sideFourText', action='store', type='string', dest='sideFourText', help='Subhead text')
        self.OptionParser.add_option('--sideFourHint', action='store', type='string', dest='sideFourHint', help='Subhead hint')
        self.OptionParser.add_option('--sideFourIcon', action='store', type='string', dest='sideFourIcon', help='Subhead icon')

        self.OptionParser.add_option('--bottomText', action='store', type='string', dest='bottomText', help='Subhead text')
        self.OptionParser.add_option('--bottomHint', action='store', type='string', dest='bottomHint', help='Subhead hint')
        self.OptionParser.add_option('--bottomIcon', action='store', type='string', dest='bottomIcon', help='Subhead icon')

        # Inkscape param workaround.
        self.OptionParser.add_option("--yappi_config")
        self.OptionParser.add_option("--yappi_side_i")
        self.OptionParser.add_option("--yappi_side_ii")
        self.OptionParser.add_option("--yappi_side_iii")
        self.OptionParser.add_option("--yappi_side_iv")
        self.OptionParser.add_option("--yappi_bottom")

    def __getattr__(self, name):
        # Try to redirect access to option values.
        if hasattr(self.options, name):
            return getattr(self.options, name)

        return None

    def effect(self):
        # Fetch the svg root element ...
        svg = self.document.getroot()

        # ... as well as the image width and height.
        width  = self.unittouu(svg.get('width'))
        height = self.unittouu(svg.get('height'))

        # Fetch the extention parameters.
        self.logoPath = self.options.logoPath if self.options.logoPath is not None and os.path.isfile(self.options.logoPath) else None
        self.sideOneIcon = self.options.sideOneIcon if self.options.sideOneIcon is not None and os.path.isfile(self.options.sideOneIcon) else None
        self.sideTwoIcon = self.options.sideTwoIcon if self.options.sideTwoIcon is not None and os.path.isfile(self.options.sideTwoIcon) else None
        self.sideThreeIcon = self.options.sideThreeIcon if self.options.sideThreeIcon is not None and  os.path.isfile(self.options.sideThreeIcon) else None
        self.sideFourIcon = self.options.sideFourIcon if self.options.sideFourIcon is not None and os.path.isfile(self.options.sideFourIcon) else None
        self.bottomIcon = self.options.bottomIcon if self.options.bottomIcon is not None and os.path.isfile(self.options.bottomIcon) else None

        # Create a new layer, ...
        layer = inkex.etree.SubElement(svg, 'g')
        layer.set(inkex.addNS('label', 'inkscape'), 'Basic Shape')
        layer.set(inkex.addNS('groupmode', 'inkscape'), 'layer')

        # ... define and calculate the dimensions (in mm) of the basic shape ...
        cubeWidth = self.unittouu("8.5 cm")
        cubeHeight = self.unittouu("2.5 cm")
        cubeDepth = self.unittouu("5.6 cm")

        wingHeight = self.unittouu("1.0 cm")
        smallWingWidth = cubeDepth - 2 * wingHeight
        largeWingWidth = cubeWidth - 2 * wingHeight

        padding = wingHeight
        borderWidth = 1

        raspiUsbWidth = self.unittouu("1.5 cm")
        raspiUsbHeight = self.unittouu("1.6 cm")
        raspiEthWidth = self.unittouu("1.6 cm")
        raspiEthHeight = self.unittouu("1.4 cm")
        raspiSoundWidth = raspiSoundHeight = self.unittouu("0.7 cm")
        raspiHdmiWidth = self.unittouu("1.6 cm")
        raspiHdmiHeight = self.unittouu("0.5 cm")
        raspiMusbWidth = self.unittouu("0.9 cm")
        raspiMusbHeight = self.unittouu("0.4 cm")
        raspiSdCardWidth = self.unittouu("1.2 cm")
        raspiSdCardHeight = self.unittouu("0.3 cm")

        raspiUsb1OffsetX = padding + wingHeight + cubeHeight + self.unittouu("0.2 cm")
        raspiUsb1OffsetY = padding + wingHeight + cubeHeight - self.unittouu("0.3 cm")
        raspiUsb2OffsetX = padding + wingHeight + cubeHeight + self.unittouu("2.0 cm")
        raspiUsb2OffsetY = padding + wingHeight + cubeHeight - self.unittouu("0.3 cm")
        raspiEthOffsetX = padding + wingHeight + cubeHeight + self.unittouu("3.8 cm")
        raspiEthOffsetY = padding + wingHeight + cubeHeight - self.unittouu("0.3 cm")
        raspiSoundOffsetX = padding + wingHeight + cubeHeight + cubeDepth + self.unittouu("0.3 cm")
        raspiSoundOffsetY = padding + wingHeight + cubeHeight + self.unittouu("3.5 cm")
        raspiHdmiOffsetX = padding + wingHeight + cubeHeight + cubeDepth + self.unittouu("0.3 cm")
        raspiHdmiOffsetY = padding + wingHeight + cubeHeight + self.unittouu("6.0 cm")
        raspiMusbOffsetX = padding + wingHeight + cubeHeight + cubeDepth + self.unittouu("0.3 cm")
        raspiMusbOffsetY = padding + wingHeight + cubeHeight + self.unittouu("7.9 cm")
        raspiSdCardOffsetX = padding + wingHeight + cubeHeight + self.unittouu("2.2 cm")
        raspiSdCardOffsetY = padding + wingHeight + cubeHeight + cubeWidth

        # ... and the headline boxes.
        boxWidth = cubeWidth
        boxHeight = cubeHeight / 4
        boxBorderColor = 'ffffff'
        boxBorder = 0
        
        # Draw the basic shape (cutting edges), ...
        self.drawPolygon(
            borderWidth, self.borderColor, self.mainBgColor, False, layer,
            (padding, padding + cubeHeight + cubeWidth),
            (padding + 2 * wingHeight + cubeHeight, padding + 2 * wingHeight + 2 * cubeHeight + cubeWidth),
            (padding + cubeHeight + cubeDepth, padding + 2 * wingHeight + 2 * cubeHeight + cubeWidth),
            (padding + wingHeight + 2 * cubeHeight + cubeDepth, padding + wingHeight + cubeHeight + cubeWidth),
            (padding + 2 * wingHeight + 2 * cubeHeight + cubeDepth, padding + 2 * wingHeight + cubeHeight + cubeWidth),
            (padding + 2 * wingHeight + 2 * cubeHeight + cubeDepth + smallWingWidth, padding + 2 * wingHeight + cubeHeight + cubeWidth),
            (padding + 2 * wingHeight + 2 * cubeHeight + 2 * cubeDepth, padding + 2 * wingHeight + cubeHeight + largeWingWidth),
            (padding + 2 * wingHeight + 2 * cubeHeight + 2 * cubeDepth, padding + 2 * wingHeight + cubeHeight),
            (padding + 2 * cubeHeight + 2 * cubeDepth, padding + cubeHeight),
            (padding + 2 * wingHeight + 2 * cubeHeight + cubeDepth, padding + cubeHeight),
            (padding + wingHeight + 2 * cubeHeight + cubeDepth, padding + cubeHeight + wingHeight),
            (padding + cubeHeight + cubeDepth, padding),
            (padding + 2 * wingHeight + cubeHeight, padding),
            (padding, padding + 2 * wingHeight + cubeHeight),
            (padding, padding + cubeHeight + cubeWidth),
        )

        # ... the inner edges, ...
        self.drawPolygon(
            borderWidth, self.borderColor, None, True, layer,
            (padding + wingHeight + cubeHeight, padding + wingHeight + cubeHeight + cubeWidth),
            (padding + wingHeight + 2 * cubeHeight + 2 * cubeDepth, padding + wingHeight + cubeHeight + cubeWidth),
            (padding + wingHeight + 2 * cubeHeight + 2 * cubeDepth, padding + wingHeight + cubeHeight),
            (padding + wingHeight + cubeHeight, padding + wingHeight + cubeHeight),
            (padding + wingHeight + cubeHeight, padding + wingHeight + cubeHeight + cubeWidth)
        )

        # ... the wing folding edges, ...
        self.drawLine(
            padding + wingHeight + 2 * cubeHeight + cubeDepth, padding + wingHeight + cubeHeight + cubeWidth,
            padding + 2 * wingHeight + 2 * cubeHeight + cubeDepth, padding + wingHeight + cubeHeight + cubeWidth,
            borderWidth, self.borderColor, False, layer)

        self.drawLine(
            padding + wingHeight + 2 * cubeHeight + 2 * cubeDepth, padding + wingHeight + cubeHeight + cubeWidth,
            padding + 2 * cubeHeight + 2 * cubeDepth, padding + wingHeight + cubeHeight + cubeWidth,
            borderWidth, self.borderColor, False, layer)

        self.drawLine(
            padding + wingHeight + 2 * cubeHeight + 2 * cubeDepth, padding + wingHeight + cubeHeight + cubeWidth,
            padding + wingHeight + 2 * cubeHeight + 2 * cubeDepth, padding + cubeHeight + cubeWidth,
            borderWidth, self.borderColor, False, layer)

        self.drawLine(
            padding + wingHeight + 2 * cubeHeight + 2 * cubeDepth, padding + wingHeight + cubeHeight,
            padding + wingHeight + 2 * cubeHeight + 2 * cubeDepth, padding + 2 * wingHeight + cubeHeight,
            borderWidth, self.borderColor, False, layer)

        self.drawLine(
            padding + wingHeight + 2 * cubeHeight + 2 * cubeDepth, padding + wingHeight + cubeHeight,
            padding + 2 * cubeHeight + 2 * cubeDepth, padding + wingHeight + cubeHeight,
            borderWidth, self.borderColor, False, layer)

        self.drawLine(
            padding + wingHeight + 2 * cubeHeight + cubeDepth, padding + wingHeight + cubeHeight,
            padding + 2 * wingHeight + 2 * cubeHeight + cubeDepth, padding + wingHeight + cubeHeight,
            borderWidth, self.borderColor, False, layer)

        # ... the triangle folding edges, ...
        self.drawLine(
            padding + wingHeight, padding + wingHeight + cubeHeight + cubeWidth, 
            padding + wingHeight + cubeHeight, padding + wingHeight + cubeHeight + cubeWidth, 
            borderWidth, self.borderColor, True, layer)

        self.drawLine(
            padding + wingHeight + cubeHeight, padding + wingHeight + cubeHeight + cubeWidth, 
            padding + wingHeight + cubeHeight, padding + wingHeight + 2 * cubeHeight + cubeWidth, 
            borderWidth, self.borderColor, True, layer)

        self.drawLine(
            padding + wingHeight + cubeHeight + cubeDepth, padding + wingHeight + cubeHeight + cubeWidth, 
            padding + wingHeight + cubeHeight + cubeDepth, padding + wingHeight + cubeHeight + cubeWidth + cubeHeight, 
            borderWidth, self.borderColor, True, layer)

        self.drawLine(
            padding + wingHeight + cubeHeight + cubeDepth, padding + wingHeight + cubeHeight, 
            padding + wingHeight + cubeHeight + cubeDepth, padding + wingHeight, 
            borderWidth, self.borderColor, True, layer)

        self.drawLine(
            padding + wingHeight, padding + wingHeight + cubeHeight, 
            padding + wingHeight + cubeHeight, padding + wingHeight + cubeHeight, 
            borderWidth, self.borderColor, True, layer)

        self.drawLine(
            padding + wingHeight + cubeHeight, padding + wingHeight, 
            padding + wingHeight + cubeHeight, padding + wingHeight + cubeHeight, 
            borderWidth, self.borderColor, True, layer)

        # ... the inner triangle folding edges, ...
        self.drawLine(
            padding + wingHeight + cubeHeight, padding + wingHeight + cubeHeight + cubeWidth, 
            padding + wingHeight + cubeHeight - cubeHeight / 2, padding + wingHeight + cubeHeight + cubeWidth + cubeHeight / 2, 
            borderWidth, self.borderColor, True, layer)

        self.drawLine(
            padding + wingHeight + cubeHeight + cubeDepth, padding + wingHeight + cubeHeight + cubeWidth, 
            padding + wingHeight + cubeHeight + cubeDepth + cubeHeight / 2, padding + wingHeight + cubeHeight + cubeWidth + cubeHeight / 2, 
            borderWidth, self.borderColor, True, layer)

        self.drawLine(
            padding + wingHeight + cubeHeight + cubeDepth, padding + wingHeight + cubeHeight, 
            padding + wingHeight + cubeHeight + cubeDepth + cubeHeight / 2, padding + wingHeight + cubeHeight - cubeHeight / 2, 
            borderWidth, self.borderColor, True, layer)

        self.drawLine(
            padding + wingHeight + cubeHeight, padding + wingHeight + cubeHeight, 
            padding + wingHeight + cubeHeight - cubeHeight / 2, padding + wingHeight + cubeHeight - cubeHeight / 2, 
            borderWidth, self.borderColor, True, layer)

        # ... the middle folding edges, ...
        self.drawLine(
            padding + wingHeight + cubeHeight + cubeDepth, padding + wingHeight + cubeHeight, 
            padding + wingHeight + cubeHeight + cubeDepth, padding + wingHeight + cubeHeight + cubeWidth, 
            borderWidth, self.borderColor, True, layer)

        self.drawLine(
            padding + wingHeight + 2 * cubeHeight + cubeDepth, padding + wingHeight + cubeHeight, 
            padding + wingHeight + 2 * cubeHeight + cubeDepth, padding + wingHeight + cubeHeight + cubeWidth, 
            borderWidth, self.borderColor, True, layer)

        # ... the inner cutting edges ...
        self.drawLine(
            padding + wingHeight + cubeHeight + wingHeight / 2, padding + wingHeight, 
            padding + wingHeight + cubeHeight + cubeDepth - wingHeight / 2, padding + wingHeight, 
            borderWidth, self.borderColor, False, layer)

        self.drawLine(
            padding + wingHeight, padding + wingHeight + cubeHeight + wingHeight / 2, 
            padding + wingHeight, padding + wingHeight + cubeHeight + cubeWidth - wingHeight / 2, 
            borderWidth, self.borderColor, False, layer)

        self.drawLine(
            padding + wingHeight + cubeHeight + wingHeight / 2, padding + wingHeight + 2 * cubeHeight + cubeWidth, 
            padding + wingHeight + cubeHeight + cubeDepth - wingHeight / 2, padding + wingHeight + 2 * cubeHeight + cubeWidth, 
            borderWidth, self.borderColor, False, layer)

        # ... and the slots.
        self.drawPolygon(
            borderWidth, self.borderColor, self.mainBgColor, False, layer,
            (raspiUsb1OffsetX, raspiUsb1OffsetY),
            (raspiUsb1OffsetX + raspiUsbWidth, raspiUsb1OffsetY),
            (raspiUsb1OffsetX + raspiUsbWidth, raspiUsb1OffsetY - raspiUsbHeight),
            (raspiUsb1OffsetX, raspiUsb1OffsetY - raspiUsbHeight),
            (raspiUsb1OffsetX, raspiUsb1OffsetY)
        )

        self.drawPolygon(
            borderWidth, self.borderColor, self.mainBgColor, False, layer,
            (raspiUsb2OffsetX, raspiUsb2OffsetY),
            (raspiUsb2OffsetX + raspiUsbWidth, raspiUsb2OffsetY),
            (raspiUsb2OffsetX + raspiUsbWidth, raspiUsb2OffsetY - raspiUsbHeight),
            (raspiUsb2OffsetX, raspiUsb2OffsetY - raspiUsbHeight),
            (raspiUsb2OffsetX, raspiUsb2OffsetY)
        )

        self.drawPolygon(
            borderWidth, self.borderColor, self.mainBgColor, False, layer,
            (raspiEthOffsetX, raspiEthOffsetY),
            (raspiEthOffsetX + raspiEthWidth, raspiEthOffsetY),
            (raspiEthOffsetX + raspiEthWidth, raspiEthOffsetY - raspiEthHeight),
            (raspiEthOffsetX, raspiEthOffsetY - raspiEthHeight),
            (raspiEthOffsetX, raspiEthOffsetY)
        )

        self.drawPolygon(
            borderWidth, self.borderColor, self.mainBgColor, False, layer,
            (raspiSoundOffsetX, raspiSoundOffsetY),
            (raspiSoundOffsetX + raspiSoundHeight, raspiSoundOffsetY),
            (raspiSoundOffsetX + raspiSoundHeight, raspiSoundOffsetY - raspiSoundWidth),
            (raspiSoundOffsetX, raspiSoundOffsetY - raspiSoundWidth),
            (raspiSoundOffsetX, raspiSoundOffsetY)
        )

        self.drawPolygon(
            borderWidth, self.borderColor, self.mainBgColor, False, layer,
            (raspiHdmiOffsetX, raspiHdmiOffsetY),
            (raspiHdmiOffsetX + raspiHdmiHeight, raspiHdmiOffsetY),
            (raspiHdmiOffsetX + raspiHdmiHeight, raspiHdmiOffsetY - raspiHdmiWidth),
            (raspiHdmiOffsetX, raspiHdmiOffsetY - raspiHdmiWidth),
            (raspiHdmiOffsetX, raspiHdmiOffsetY)
        )

        self.drawPolygon(
            borderWidth, self.borderColor, self.mainBgColor, False, layer,
            (raspiMusbOffsetX, raspiMusbOffsetY),
            (raspiMusbOffsetX + raspiMusbHeight, raspiMusbOffsetY),
            (raspiMusbOffsetX + raspiMusbHeight, raspiMusbOffsetY - raspiMusbWidth),
            (raspiMusbOffsetX, raspiMusbOffsetY - raspiMusbWidth),
            (raspiMusbOffsetX, raspiMusbOffsetY)
        )

        self.drawPolygon(
            borderWidth, self.borderColor, self.mainBgColor, False, layer,
            (raspiSdCardOffsetX, raspiSdCardOffsetY),
            (raspiSdCardOffsetX + raspiSdCardWidth, raspiSdCardOffsetY),
            (raspiSdCardOffsetX + raspiSdCardWidth, raspiSdCardOffsetY - raspiSdCardHeight),
            (raspiSdCardOffsetX, raspiSdCardOffsetY - raspiSdCardHeight),
            (raspiSdCardOffsetX, raspiSdCardOffsetY)
        )



        # self.drawPolygon(
        #     borderWidth, self.borderColor, self.mainBgColor, False, layer,
        #     (padding + wingHeight, padding + wingHeight + blockHeight),
        #     (padding + wingHeight + 2 * blockWidth, padding + wingHeight + blockHeight),
        #     (padding + 2 * blockWidth, padding + blockHeight),
        #     (padding + 2 * blockWidth, padding + 2 * wingHeight),
        #     (padding + 2 * wingHeight + 2 * blockWidth, padding),
        #     (padding + 3 * blockWidth, padding),
        #     (padding + 2 * wingHeight + 3 * blockWidth, padding + 2 * wingHeight),
        #     (padding + 2 * wingHeight + 3 * blockWidth, padding + blockHeight),
        #     (padding + wingHeight + 3 * blockWidth, padding + wingHeight + blockHeight),
        #     (padding + wingHeight + 3 * blockWidth, padding + wingHeight + blockHeight),
        #     (padding + wingHeight + 4 * blockWidth, padding + wingHeight + blockHeight),
        #     (padding + wingHeight + 4 * blockWidth, padding + wingHeight + 2 * blockHeight),
        #     (padding + wingHeight + 2 * blockWidth, padding + wingHeight + 2 * blockHeight),
        #     (padding + 2 * wingHeight + 2 * blockWidth, padding + 2 * wingHeight + 2 * blockHeight),
        #     (padding + 2 * wingHeight + 2 * blockWidth, padding + 3 * blockHeight),
        #     (padding + 2 * blockWidth, padding + 2 * wingHeight + 3 * blockHeight),
        #     (padding + 2 * wingHeight + blockWidth, padding + 2 * wingHeight + 3 * blockHeight),
        #     (padding + blockWidth, padding + 3 * blockHeight),
        #     (padding + blockWidth, padding + 2 * wingHeight + 2 * blockHeight),
        #     (padding + wingHeight + blockWidth, padding + wingHeight + 2 * blockHeight),
        #     (padding + wingHeight, padding + wingHeight + 2 * blockHeight),
        #     (padding, padding + 2 * blockHeight),
        #     (padding, padding + 2 * wingHeight + blockHeight),
        #     (padding + wingHeight, padding + wingHeight + blockHeight))

        # ... the inner edges ...
        # self.drawLine(padding + wingHeight, padding + wingHeight + blockHeight, padding + wingHeight,  padding + wingHeight + 2 * blockHeight, borderWidth, self.borderColor, True, layer)
        # self.drawLine(padding + wingHeight + blockWidth, padding + wingHeight + blockWidth, padding + wingHeight + blockWidth,  padding + wingHeight + 2 * blockWidth, borderWidth, self.borderColor, True, layer)
        # self.drawLine(padding + wingHeight + 2 * blockWidth, padding + wingHeight + blockWidth, padding + wingHeight + 2 * blockWidth,  padding + wingHeight + 2 * blockWidth, borderWidth, self.borderColor, True, layer)
        # self.drawLine(padding + wingHeight + 3 * blockWidth, padding + wingHeight + blockWidth, padding + wingHeight + 3 * blockWidth,  padding + wingHeight + 2 * blockWidth, borderWidth, self.borderColor, True, layer)

        # self.drawPolygon(
        #     borderWidth, self.borderColor, None, True, layer,
        #     (padding + wingHeight + blockWidth, padding + wingHeight + 2 * blockHeight),
        #     (padding + wingHeight + blockWidth, padding + wingHeight + 3 * blockHeight),
        #     (padding + wingHeight + 2 * blockWidth, padding + wingHeight + 3 * blockHeight),
        #     (padding + wingHeight + 2 * blockWidth, padding + wingHeight + 2 * blockHeight),
        #     (padding + wingHeight + blockWidth, padding + wingHeight + 2 * blockHeight))

        # self.drawPolygon(
        #     borderWidth, self.borderColor, None, True, layer,
        #     (padding + wingHeight + 2 * blockWidth, padding + wingHeight + blockHeight),
        #     (padding + wingHeight + 2 * blockWidth, padding + wingHeight), 
        #     (padding + wingHeight + 3 * blockWidth, padding + wingHeight),
        #     (padding + wingHeight + 3 * blockWidth, padding + wingHeight + blockHeight),
        #     (padding + wingHeight + 2 * blockWidth, padding + wingHeight + blockHeight))

        # ... and the headline boxes.
        # self.drawSideFooter(padding + wingHeight, padding + 2 * blockHeight + wingHeight - boxHeight, boxWidth, boxHeight, boxBorder, boxBorderColor, svg, self.sideOneText, self.titleBgColor, self.titleColor, boxHeight / 5, self.sideOneHint, self.hintBgColor, self.hintColor, boxHeight / 25 * 3, self.sideOneIcon)
        # self.drawSideFooter(padding + wingHeight + blockWidth, padding + 2 * blockHeight + wingHeight - boxHeight, boxWidth, boxHeight, boxBorder, boxBorderColor, svg, self.sideTwoText, self.titleBgColor, self.titleColor, boxHeight / 5, self.sideTwoHint, self.hintBgColor, self.hintColor, boxHeight / 25 * 3, self.sideTwoIcon)
        # self.drawSideFooter(padding + wingHeight + 2 * blockWidth, padding + 2 * blockHeight + wingHeight - boxHeight, boxWidth, boxHeight, boxBorder, boxBorderColor, svg, self.sideThreeText, self.titleBgColor, self.titleColor, boxHeight / 5, self.sideThreeHint, self.hintBgColor, self.hintColor, boxHeight / 25 * 3, self.sideThreeIcon)
        # self.drawSideFooter(padding + wingHeight + 3 * blockWidth, padding + 2 * blockHeight + wingHeight - boxHeight, boxWidth, boxHeight, boxBorder, boxBorderColor, svg, self.sideFourText, self.titleBgColor, self.titleColor, boxHeight / 5, self.sideFourHint, self.hintBgColor, self.hintColor, boxHeight / 25 * 3, self.sideFourIcon)

        # attrs = {
        #     'transform' : 'rotate(90, ' + str(padding + wingHeight + blockWidth + blockWidth / 2) + ',' + str(padding + wingHeight + 2 * blockHeight + blockHeight / 2) + ')' 
        # }

        # bottomLayer = inkex.etree.SubElement(svg, 'g', attrs)
        # bottomLayer.set(inkex.addNS('label', 'inkscape'), 'Bottom Side')
        # bottomLayer.set(inkex.addNS('groupmode', 'inkscape'), 'layer')

        # self.drawSideFooter(padding + wingHeight + blockWidth, padding + 3 * blockHeight + wingHeight - boxHeight, boxWidth, boxHeight, boxBorder, boxBorderColor, bottomLayer, self.bottomText, self.titleBgColor, self.titleColor, boxHeight / 5, self.bottomHint, self.hintBgColor, self.hintColor, boxHeight / 25 * 3, self.bottomIcon)

        # Finally embedd the main logo.
        # if self.logoPath is not None:
        #     self.innerImage(padding + wingHeight + 2 * blockWidth, padding + wingHeight, blockWidth, blockHeight, padding, self.logoPath, svg)
        # else:
        #     self.log('No path to logo given!')

    def drawSideFooter(self, x, y, w, h, border, borderColor, parent, title, titleBg, titleColor, titleSize, hint, hintBg, hintColor, hintSize, logoPath):
        layer = inkex.etree.SubElement(parent, 'g')
        layer.set(inkex.addNS('label', 'inkscape'), 'Footer')
        layer.set(inkex.addNS('groupmode', 'inkscape'), 'layer')

        self.drawTextBox(x, y, w, h, border, borderColor, titleBg, layer, title, titleColor, titleSize, True)
        self.drawTextBox(x, y - h / 5 , w, h / 5, border, borderColor, hintBg, layer, hint, hintColor, hintSize, False)

        if logoPath is not None:
            self.innerImage(x + w - h / 10 * 12, y, h, h, h / 10, logoPath, layer)
        else:
            self.log('No path to logo given!')

    def drawTextBox(self, x, y, w, h, border, borderColor, fillColor, parent, msg, fontColor, fontSize, boldFace):
        # Create a new layer.
        layer = inkex.etree.SubElement(parent, 'g')
        layer.set(inkex.addNS('label', 'inkscape'), 'Headline Layer')
        layer.set(inkex.addNS('groupmode', 'inkscape'), 'layer')

        # Draw the actual textbox, ...
        box = self.drawRectangle(x, y, w, h, border, borderColor, fillColor, layer)

        # ... create the text element, ...
        text = inkex.etree.SubElement(layer, inkex.addNS('text','svg'))
        text.set('x', str(x + fontSize))
        text.set('y', str(y + h / 2 + fontSize / 2))
        text.set('fill', '#' + str(fontColor));
        text.text = str(msg)

        # ... define text style and position ...
        style = {
            'font-weight' : 'bold' if boldFace else 'normal',
            'font-size': str(fontSize)
        }

        # ... and finally set the text style.
        text.set('style', formatStyle(style))

    def drawLine(self, x1, y1, x2, y2, width, color, dashed, parent):
        dashStyle = '5,3,2' if dashed else 'none'

        style = { 
            'stroke': '#' + str(color),
            'stroke-width' : width,
            'stroke-dasharray' : dashStyle,
            'fill' : 'none'
        }

        attrs = {
            'style' : formatStyle(style),
            inkex.addNS('label','inkscape') : 'A Name',
            'd' : 'M ' + str(x1) + ',' + str(y1) + ' L ' + str(x2) + ',' + str(y2)
        }

        return inkex.etree.SubElement(parent, inkex.addNS('path','svg'), attrs)

    def drawRectangle(self, x, y, w, h, border, borderColor, fillColor, parent):
        # Define the rectangle style ...
        stroke = '#' + str(borderColor) if border > 0 else 'none'

        style = { 
            'stroke' : stroke, 
            'stoke-width' : str(border), 
            'fill' : '#' + str(fillColor)
        }
                
        attrs = {
            'style' : formatStyle(style),
            'x' : str(x),
            'y' : str(y),
            'width' : str(w),
            'height' : str(h)        
        }

        return inkex.etree.SubElement(parent, inkex.addNS('rect','svg'), attrs)

    def drawPolygon(self, width, color, bgColor, dashed, parent, *points):
        dashStyle = '5,3,2' if dashed else 'none'

        style = { 
            'stroke': '#' + str(color),
            'stroke-width' : width,
            'stroke-dasharray' : dashStyle,
            'stroke-linejoin' : 'round', 
            'fill' : '#' + str(bgColor) if bgColor is not None else 'none'
        }

        counter = 0
        pointList = ''
        for p in points:
            if counter == 0:
                pointList += 'M ' + str(p[0]) + ',' + str(p[1])
            else:
                pointList += ' L ' + str(p[0]) + ',' + str(p[1]) + ' '
            counter += 1

        attrs = {
            'style' : formatStyle(style),
            'd' : pointList
        }        

        return inkex.etree.SubElement(parent, inkex.addNS('path','svg'), attrs)

    def innerImage(self, x, y, width, height, padding, path, parent):
        with codecs.open(path, encoding="utf-8") as f:
            doc = etree.parse(f).getroot()

            imgWidth = self.unittouu(doc.get('width'))
            imgHeight = self.unittouu(doc.get('height'))

            sx = (width - padding) / imgWidth
            sy = (height - padding) / imgHeight

            scale = sx
            if sy < sx:
                scale = sy 

            x += width / 2 - imgWidth * scale / 2
            y += height / 2 - imgHeight * scale / 2

            attrs = {
                'transform' : 'translate(' + str(x) + ',' + str(y) + ') scale(' + str(scale) + ',' + str(scale) + ')' 
            }

            logoLayer = inkex.etree.SubElement(parent, 'g', attrs)
            logoLayer.set(inkex.addNS('label', 'inkscape'), 'Logo Layer')
            logoLayer.set(inkex.addNS('groupmode', 'inkscape'), 'layer')
            logoLayer.append(deepcopy(doc))

    def embeddImage(self, x, y, width, height, path, parent):
        attrs = {
            'x' : str(x),
            'y' : str(y),
            'width' : str(width),
            'height' : str(height)
        }

        return inkex.etree.SubElement(parent, inkex.addNS('image','xml'), attrs)

    def formatTextBlock(self, x, y, textList, fontSize, fontColor, bgColor, parent):
        # Create the text element, ...
        textItem = inkex.etree.SubElement(parent, inkex.addNS('text','svg'))
        textItem.set('x', str(x))
        textItem.set('y', str(y))
        textItem.set('fill', '#' + str(fontColor));

        # ... define text style and position ...
        style = {
            'font-size': str(fontSize)
        }

        # ... and set the text style.
        textItem.set('style', formatStyle(style))

        # Step the top padding.
        stepY = 1

        # Finally add all lines as tspans.
        for text in textList:
            if text != '':
                self.formatText(x, y + stepY * fontSize * 1.2, text, fontColor, bgColor, textItem)
                stepY += 1

    def formatText(self, x, y, text, fontColor, bgColor, parent):
        # Declare the bbcode regex, ...
        bbCodeRegex = re.compile(r'\[(/)?((?(1)(i|b|color)|(i|b|color=[0-9a-fA-F]{3,6})))\]', re.IGNORECASE)

        # ... and check for matches.
        if not bbCodeRegex.findall(text):
            self.positonTspan(x, y, '_', bgColor, parent)
            self.createTspan(text, fontColor, parent)
            return

        # If there are matches fetch all of them.
        matches = bbCodeRegex.finditer(text)

        # Initialize the basic style, ...
        bbStyles = {
            'b' : False,
            'i' : False,
            'color' : fontColor
        }

        # ... and the processing stack.
        stack = Stack()

        # Add a positioning tspan.
        self.positonTspan(x, y, '_', bgColor, parent)

        # Remember the last match position.
        lastMatch = 0

        # Loop over all matches.
        for m in matches:
             # Extract important data from match.
            textChunk = text[lastMatch:m.start()]
            lastMatch = m.start() + len(str(m.group()))
            isClosing = False if m.groups()[0] == None else True
            bbTagName = m.groups()[1].split('=')[0]

            # Setup the basic tspan style.
            style = {
                'font-weight' : 'bold' if bbStyles['b'] else 'normal',
                'font-style' : 'italic' if bbStyles['i'] else 'normal',
                'fill' : '#' + str(bbStyles['color'])
            }

            # Update the current style.
            if isClosing and stack.peek()[0] == bbTagName:
                bbStyles[bbTagName] = stack.pop()[1]
            elif isClosing is False and bbTagName == 'color':
                stack.push((bbTagName, bbStyles[bbTagName]))
                bbStyles[bbTagName] = m.groups()[1].split('=')[1]
            elif isClosing is False:
                stack.push((bbTagName, bbStyles[bbTagName]))
                bbStyles[bbTagName] = False if bbStyles[bbTagName] else True
                
            if len(textChunk) > 0:
                # Prepend spaces.
                if textChunk[0] == ' ':
                    self.createTspan('_', bgColor, parent)

                # Create the new tspan element.
                tspan = inkex.etree.SubElement(parent, inkex.addNS('tspan', 'svg'))
                tspan.set('style', formatStyle(style))
                tspan.text = textChunk

                # Append spaces.
                if textChunk[-1] == ' ' and len(textChunk) > 1:
                    self.createTspan('_', bgColor, parent)

        if len(text) > 0:
            textChunk = text[lastMatch:]
                
            if len(textChunk.strip()) > 0:
                # Setup the basic tspan style.
                style = {
                    'font-weight' : 'bold' if bbStyles['b'] else 'normal',
                    'font-style' : 'italic' if bbStyles['i'] else 'normal',
                    'fill' : '#' + str(bbStyles['color'])
                }

                # Prepend spaces.
                if textChunk[0] == ' ':
                    self.createTspan('_', bgColor, parent)

                # Create the new tspan element.
                tspan = inkex.etree.SubElement(parent, inkex.addNS('tspan', 'svg'))
                tspan.set('style', formatStyle(style))
                tspan.text = textChunk

    
    def positonTspan(self, x, y, text, fontColor, parent):
        # Create the new tspan element.
        tspan = self.createTspan(text, fontColor, parent)
        tspan.set('x', str(x))
        tspan.set('y', str(y))
            
    def createTspan(self, text, fontColor, parent):
        # Setup the basic tspan style.
        style = {
            'fill' : '#' + str(fontColor)
        }
                
        # Create the new tspan element.
        tspan = inkex.etree.SubElement(parent, inkex.addNS('tspan', 'svg'))
        tspan.set('style', formatStyle(style))
        tspan.text = text

        return tspan

    def log(self, msg):
        with open(self.logFile, 'a+') as log:
            log.write(str(msg) + '\n')

def main(argv):
    yappi = Yappi()
    yappi.affect()

if __name__ == "__main__":
    main(sys.argv[1:])
