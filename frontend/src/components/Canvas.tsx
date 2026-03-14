'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ZoomIn, ZoomOut, RotateCcw, Maximize2 } from 'lucide-react'

interface CanvasProps {
  svg?: string
  className?: string
}

export function Canvas({ svg, className = '' }: CanvasProps) {
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [lastPanPosition, setLastPanPosition] = useState({ x: 0, y: 0 })
  const canvasRef = useRef<HTMLDivElement>(null)
  const wheelRef = useRef<HTMLDivElement>(null)
  
  // Log when SVG changes
  useEffect(() => {
    console.log('Canvas: SVG prop changed, length:', svg?.length || 0);
    if (svg) {
      console.log('Canvas: SVG preview:', svg.substring(0, 100));
    }
  }, [svg])

  // Handle mouse wheel for zooming
  const handleWheel = useCallback((e: WheelEvent) => {
    e.preventDefault()
    const zoomSensitivity = 0.002
    setZoom(prevZoom => {
      const newZoom = Math.max(0.1, Math.min(5, prevZoom - e.deltaY * zoomSensitivity))
      return newZoom
    })
  }, [])

  // Handle mouse down for panning
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0) { // Left mouse button
      setIsDragging(true)
      setLastPanPosition({ x: e.clientX, y: e.clientY })
    }
  }

  // Handle mouse move for panning
  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      const deltaX = e.clientX - lastPanPosition.x
      const deltaY = e.clientY - lastPanPosition.y
      setPan(prev => ({
        x: prev.x + deltaX,
        y: prev.y + deltaY
      }))
      setLastPanPosition({ x: e.clientX, y: e.clientY })
    }
  }

  // Handle mouse up to stop panning
  const handleMouseUp = () => {
    setIsDragging(false)
  }

  // Handle zoom buttons
  const zoomIn = () => setZoom(prev => Math.min(5, prev * 1.2))
  const zoomOut = () => setZoom(prev => Math.max(0.1, prev / 1.2))
  
  // Reset view
  const resetView = () => {
    setZoom(1)
    setPan({ x: 0, y: 0 })
  }

  // Fit to screen
  const fitToScreen = useCallback(() => {
    if (canvasRef.current && svg) {
      const container = canvasRef.current
      const containerRect = container.getBoundingClientRect()
      
      // Parse SVG to get its viewBox or dimensions
      const parser = new DOMParser()
      const svgDoc = parser.parseFromString(svg, 'image/svg+xml')
      const svgElement = svgDoc.documentElement
      
      const viewBox = svgElement.getAttribute('viewBox')
      let svgWidth, svgHeight
      
      if (viewBox) {
        const [, , width, height] = viewBox.split(' ').map(Number)
        svgWidth = width
        svgHeight = height
      } else {
        svgWidth = parseFloat(svgElement.getAttribute('width') || '100')
        svgHeight = parseFloat(svgElement.getAttribute('height') || '100')
      }
      
      const scaleX = containerRect.width / svgWidth
      const scaleY = containerRect.height / svgHeight
      const scale = Math.min(scaleX, scaleY) * 0.8 // 80% to add some padding
      
      setZoom(scale)
      setPan({ x: 0, y: 0 })
    }
  }, [svg])

  // Fit to screen when SVG changes
  useEffect(() => {
    if (svg) {
      setTimeout(fitToScreen, 100) // Small delay to ensure DOM is updated
    }
  }, [svg, fitToScreen])

  // Set up wheel event listener with passive: false
  useEffect(() => {
    const element = wheelRef.current || canvasRef.current
    if (!element) return

    // Add wheel event listener with passive: false to allow preventDefault
    element.addEventListener('wheel', handleWheel, { passive: false })
    
    return () => {
      element.removeEventListener('wheel', handleWheel)
    }
  }, [handleWheel])

  // Clean up event listeners
  useEffect(() => {
    const handleGlobalMouseUp = () => setIsDragging(false)
    document.addEventListener('mouseup', handleGlobalMouseUp)
    return () => document.removeEventListener('mouseup', handleGlobalMouseUp)
  }, [])

  const renderPlaceholder = () => (
    <div className="flex items-center justify-center h-full text-muted-foreground">
      <div className="text-center">
        <div className="text-6xl mb-4">📐</div>
        <h3 className="text-lg font-medium mb-2">No Design Yet</h3>
        <p className="text-sm">
          Start a conversation with the assistant to generate your first part design.
        </p>
      </div>
    </div>
  )

  const renderSvg = () => {
    if (!svg) return null

    return (
      <div className="absolute inset-0 overflow-hidden">
        <div
          className="w-full h-full flex items-center justify-center"
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: 'center',
            cursor: isDragging ? 'grabbing' : 'grab'
          }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
        >
          <div
            dangerouslySetInnerHTML={{ __html: svg }}
            className="select-none"
            style={{
              maxWidth: '100%',
              maxHeight: '100%',
              objectFit: 'contain'
            }}
          />
          
          {/* Dimension annotations overlay */}
          <div className="absolute inset-0 pointer-events-none">
            {/* Add dimension lines and annotations here if needed */}
          </div>
        </div>
      </div>
    )
  }

  return (
    <Card className={`relative ${className}`}>
      {/* Header with controls */}
      <div className="absolute top-4 left-4 right-4 z-10 flex justify-between items-center">
        <div className="bg-background/80 backdrop-blur-sm rounded-lg p-2">
          <h2 className="text-lg font-semibold">Part Canvas</h2>
        </div>
        
        <div className="flex gap-2">
          <div className="bg-background/80 backdrop-blur-sm rounded-lg p-1 flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={zoomOut}
              disabled={zoom <= 0.1}
            >
              <ZoomOut className="w-4 h-4" />
            </Button>
            <div className="px-2 py-1 text-sm font-mono min-w-[4rem] text-center">
              {Math.round(zoom * 100)}%
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={zoomIn}
              disabled={zoom >= 5}
            >
              <ZoomIn className="w-4 h-4" />
            </Button>
          </div>
          
          <div className="bg-background/80 backdrop-blur-sm rounded-lg p-1 flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={resetView}
              title="Reset View"
            >
              <RotateCcw className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={fitToScreen}
              title="Fit to Screen"
              disabled={!svg}
            >
              <Maximize2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Canvas area */}
      <div
        ref={(el) => {
          canvasRef.current = el
          wheelRef.current = el
        }}
        className="h-full pt-16 bg-gradient-to-br from-background to-muted/20"
        style={{ minHeight: '400px' }}
      >
        {svg ? renderSvg() : renderPlaceholder()}
      </div>

      {/* Grid pattern overlay */}
      <div className="absolute inset-0 pointer-events-none opacity-5">
        <svg width="100%" height="100%">
          <defs>
            <pattern
              id="grid"
              width="20"
              height="20"
              patternUnits="userSpaceOnUse"
            >
              <path
                d="M 20 0 L 0 0 0 20"
                fill="none"
                stroke="currentColor"
                strokeWidth="1"
              />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </div>

      {/* Coordinates display */}
      {isDragging && (
        <div className="absolute bottom-4 right-4 bg-background/80 backdrop-blur-sm rounded px-2 py-1 text-xs font-mono">
          Pan: ({Math.round(pan.x)}, {Math.round(pan.y)})
        </div>
      )}
    </Card>
  )
}
