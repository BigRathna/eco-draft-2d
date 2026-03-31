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
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable"
import { apiClient } from '@/lib/api'
import { toast } from 'sonner'
import { useEngineering } from '@/lib/engineeringContext'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

export default function Home() {
  const { theme, setTheme } = useTheme()
  const [currentSvg, setCurrentSvg] = useState<string>()
  const [showAnalytics, setShowAnalytics] = useState(true)
  const [mounted, setMounted] = useState(false)
  const [triggerCheck, setTriggerCheck] = useState(0)
  const [triggerAnalysis, setTriggerAnalysis] = useState(0)
  const [triggerOptimization, setTriggerOptimization] = useState(0)
  const [externalIntent, setExternalIntent] = useState<string>('')
  
  const { partType, geometryData, material, thickness, setEngineeringData } = useEngineering()
  const queryClient = useQueryClient()

  const { data: sessionData } = useQuery({
    queryKey: ['sessionGraph'],
    queryFn: () => apiClient.getSessionGraph()
  })

  const checkoutMutation = useMutation({
    mutationFn: (version: string) => apiClient.checkoutVersion(version),
    onSuccess: (data) => {
      const parsed = data;
      toast.success(`Checked out ${parsed.part_type} (v${parsed.cached_data.version})`);
      
      const svgContent = parsed.cached_data.svg ? atob(parsed.cached_data.svg) : '';
      setCurrentSvg(svgContent);
      setEngineeringData({
        partType: parsed.part_type,
        parameters: parsed.parameters,
        geometryData: parsed.geometry_data,
      });
      queryClient.invalidateQueries({ queryKey: ['sessionGraph'] });
    }
  });

  const renderVersionDropdown = () => {
    const historicalVersions = (sessionData?.events || [])
      .filter((e: any) => e.action_type === "GENERATE")
      .map((e: any) => ({
        version: e.version,
        name: e.parameters?.part_type || 'Part'
      })).reverse();
      
    const currentVersion = sessionData?.current_version || '';
      
    if (historicalVersions.length === 0) {
      return (
        <div className="flex gap-2">
          <select
            className="flex h-8 w-[140px] items-center justify-between rounded-md border border-input bg-background px-3 py-1 text-xs ring-offset-background disabled:opacity-50 shadow-sm"
            disabled
          >
            <option>hola</option>
          </select>
        </div>
      );
    }
    
    return (
      <div className="flex gap-2">
        <select
          className="flex h-8 w-[140px] items-center justify-between rounded-md border border-input bg-background px-3 py-1 text-xs ring-offset-background disabled:opacity-50 shadow-sm"
          onChange={(e) => {
            if (e.target.value && e.target.value !== currentVersion) {
              checkoutMutation.mutate(e.target.value);
            }
          }}
          value={currentVersion}
          disabled={checkoutMutation.isPending}
        >
          <option value="" disabled>Version...</option>
          {historicalVersions.map((v: any, idx: number) => (
            <option key={idx} value={v.version}>v{v.version} - {v.name}</option>
          ))}
        </select>
      </div>
    );
  };

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
          if (action.payload?.format === 'dxf' && action.payload?.content) {
            // Direct Base64 download for DXF
            const contentDecoded = atob(action.payload.content as string);
            const blobDxf = new Blob([contentDecoded], { type: 'application/dxf' });
            const urlDxf = URL.createObjectURL(blobDxf);
            const aDxf = document.createElement('a');
            aDxf.href = urlDxf;
            aDxf.download = 'part-design.dxf';
            document.body.appendChild(aDxf);
            aDxf.click();
            document.body.removeChild(aDxf);
            URL.revokeObjectURL(urlDxf);
            toast.success('DXF exported successfully!');
          } else {
            // Default to PDF drawing
            if (!partType || !geometryData) {
              toast.error('No part generated! Please generate a part before exporting.')
              return
            }
            
            const matName = material && typeof material === 'object' && 'name' in material 
                 ? material.name 
                 : (typeof material === 'string' ? material : 'steel');
                 
            const titleBlock = {
              title: `${partType.toUpperCase()} Design`,
              drawing_number: `DWG-${Date.now().toString().slice(-4)}`,
              material: String(matName),
              thickness: Number(thickness || 5.0)
            }
            
            const blob = await apiClient.buildDrawing({
               part_type: partType,
               geometry_data: geometryData,
               title_block: titleBlock
            })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = 'part-drawing.pdf'
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            URL.revokeObjectURL(url)
            toast.success('PDF drawing downloaded successfully!')
          }
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
        <ResizablePanelGroup direction="horizontal" className="flex-1">
          {/* Left Pane - Chat */}
          <ResizablePanel defaultSize={40} minSize={25} className="flex flex-col border-r">
            <Chat 
              onSvgUpdate={handleSvgUpdate} 
              onActionTrigger={handleActionTrigger}
              externalIntent={externalIntent}
            />
          </ResizablePanel>

          <ResizableHandle withHandle />

          {/* Right Pane - Canvas and Analytics */}
          <ResizablePanel defaultSize={60} minSize={30} className="flex flex-col">
            {showAnalytics ? (
              <ResizablePanelGroup direction="vertical">
                {/* Canvas with Toolbar */}
                <ResizablePanel defaultSize={50} minSize={20} className="flex flex-col flex-1 bg-muted/10">
                  <div className="h-12 border-b flex flex-none items-center justify-between px-4 bg-background">
                     <span className="text-sm font-semibold tracking-tight">Design Workspace</span>
                     {renderVersionDropdown()}
                  </div>
                  <div className="relative flex-1 min-h-0">
                    <Canvas 
                      key={currentSvg ? currentSvg.substring(0, 50) : 'empty'} 
                      svg={currentSvg} 
                      className="h-full" 
                    />
                  </div>
                </ResizablePanel>

                <ResizableHandle withHandle />

                {/* Analytics Panel */}
                <ResizablePanel defaultSize={50} minSize={20} className="border-t bg-muted/20">
                  <div className="grid grid-cols-2 gap-4 p-4 h-full overflow-y-auto">
                    <Checks className="" trigger={triggerCheck} />
                    <Analysis className="" trigger={triggerAnalysis} />
                    {process.env.NEXT_PUBLIC_ENABLE_LCA !== 'false' && <LCA className="" />}
                    <ParetoChart 
                      className={process.env.NEXT_PUBLIC_ENABLE_LCA === 'false' ? 'col-span-2' : ''} 
                      trigger={triggerOptimization} 
                      onApplySolution={(intent: string) => {
                        setExternalIntent(intent);
                        // Reset intent after a short delay so the same intent can be applied again
                        setTimeout(() => setExternalIntent(''), 500);
                      }}
                    />
                  </div>
                </ResizablePanel>
              </ResizablePanelGroup>
            ) : (
              <div className="flex flex-col flex-1 h-full bg-muted/10">
                <div className="h-12 border-b flex flex-none items-center justify-between px-4 bg-background">
                   <span className="text-sm font-semibold tracking-tight">Design Workspace</span>
                   {renderVersionDropdown()}
                </div>
                <div className="relative flex-1 min-h-0">
                  <Canvas 
                    key={currentSvg ? currentSvg.substring(0, 50) : 'empty'} 
                    svg={currentSvg} 
                    className="h-full" 
                  />
                </div>
              </div>
            )}
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </div>
  )
}
