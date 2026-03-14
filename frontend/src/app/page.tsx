'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Moon, Sun, Monitor } from 'lucide-react'
import { useTheme } from '@/components/theme-provider'
import { Chat, ChatAction } from '@/components/Chat'
import { Canvas } from '@/components/Canvas'
import { Checks } from '@/components/Checks'
import { Analysis } from '@/components/Analysis'
import { LCA } from '@/components/LCA'
import { ParetoChart } from '@/components/ParetoChart'
import { apiClient } from '@/lib/api'
import { toast } from 'sonner'

export default function Home() {
  const { theme, setTheme } = useTheme()
  const [currentSvg, setCurrentSvg] = useState<string>()
  const [showAnalytics, setShowAnalytics] = useState(true)
  const [mounted, setMounted] = useState(false)
  const [triggerCheck, setTriggerCheck] = useState(0)
  const [triggerAnalysis, setTriggerAnalysis] = useState(0)
  const [triggerOptimization, setTriggerOptimization] = useState(0)

  useEffect(() => {
    setMounted(true)
  }, [])

  const handleSvgUpdate = (svg: string) => {
    console.log('Page: Updating SVG, length:', svg?.length || 0);
    setCurrentSvg(svg)
  }

  const handleActionTrigger = async (action: ChatAction) => {
    try {
      switch (action.type) {
        case 'export':
          const blob = await apiClient.buildDrawing()
          const url = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = 'part-drawing.pdf'
          document.body.appendChild(a)
          a.click()
          document.body.removeChild(a)
          URL.revokeObjectURL(url)
          toast.success('PDF drawing downloaded successfully!')
          break
        case 'check':
          // Trigger a refetch in the Checks component
          setTriggerCheck(prev => prev + 1)
          toast.info('Running manufacturability check...')
          break
        case 'analyze':
          // Trigger a refetch in the Analysis component
          setTriggerAnalysis(prev => prev + 1)
          toast.info('Performing stress analysis...')
          break
        case 'optimize':
          // Trigger optimization in the ParetoChart component
          setTriggerOptimization(prev => prev + 1)
          toast.info('Starting optimization...')
          break
        default:
          console.log('Unknown action:', action)
      }
    } catch (error) {
      toast.error(`Failed to ${action.label.toLowerCase()}: ${error}`)
    }
  }

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Fixed Header */}
      <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
        <div className="flex h-16 items-center justify-between px-6">
          <div className="flex items-center space-x-4">
            <h1 className="text-2xl font-bold">ECO-Draft 2D</h1>
            <div className="h-4 w-px bg-border" />
            <p className="text-sm text-muted-foreground">AI-Powered Part Design</p>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <label htmlFor="analytics-toggle" className="text-sm text-muted-foreground">
                Analytics
              </label>
              <Switch
                id="analytics-toggle"
                checked={showAnalytics}
                onCheckedChange={setShowAnalytics}
              />
            </div>
            
            {mounted ? (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  if (theme === 'light') {
                    setTheme('dark')
                  } else if (theme === 'dark') {
                    setTheme('system')
                  } else {
                    setTheme('light')
                  }
                }}
              >
                {theme === 'light' ? (
                  <Moon className="h-4 w-4" />
                ) : theme === 'dark' ? (
                  <Sun className="h-4 w-4" />
                ) : (
                  <Monitor className="h-4 w-4" />
                )}
              </Button>
            ) : (
              <Button variant="ghost" size="sm" disabled>
                <Monitor className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Pane - Chat */}
        <div className="w-1/2 flex flex-col border-r">
          <Chat 
            onSvgUpdate={handleSvgUpdate} 
            onActionTrigger={handleActionTrigger}
          />
        </div>

        {/* Right Pane - Canvas and Analytics */}
        <div className="w-1/2 flex flex-col">
          {/* Canvas */}
          <div className="flex-1">
            <Canvas 
              key={currentSvg ? currentSvg.substring(0, 50) : 'empty'} 
              svg={currentSvg} 
              className="h-full" 
            />
          </div>

          {/* Analytics Panel (collapsible) */}
          {showAnalytics && (
            <div className="border-t bg-muted/20">
              <div className="grid grid-cols-2 gap-4 p-4 max-h-96 overflow-y-auto">
                <Checks className="" trigger={triggerCheck} />
                <Analysis className="" trigger={triggerAnalysis} />
                <LCA className="" />
                <ParetoChart className="" trigger={triggerOptimization} />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
