'use client'

import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Send, Bot, User, Download, Zap, CheckCircle, BarChart3, Paperclip } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query'
import { apiClient, PartGenerateRequest, queryKeys } from '@/lib/api'
import { parseChatMessage, addToHistory, setCurrentPart, clearConversationHistory, getCurrentPart } from '@/lib/nlp'
import { toast } from 'sonner'
import { useEngineering } from '@/lib/engineeringContext'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  actions?: ChatAction[]
  svg?: string
}

export interface ChatAction {
  id: string
  label: string
  type: 'generate' | 'check' | 'analyze' | 'optimize' | 'export'
  payload?: Record<string, unknown>
}

interface ChatProps {
  onSvgUpdate?: (svg: string) => void
  onActionTrigger?: (action: ChatAction) => void
  externalIntent?: string
}

function getTimeString(date: Date) {
  return date.toLocaleTimeString();
}

export function Chat({ onSvgUpdate, onActionTrigger, externalIntent }: ChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('')
  const [selectedMaterial, setSelectedMaterial] = useState('auto')
  const [selectedLlm, setSelectedLlm] = useState('gemini')
  const queryClient = useQueryClient()
  const [timeStrings, setTimeStrings] = useState<string[]>([]);
  const [showModificationHint, setShowModificationHint] = useState(false)
  const [lastParsedParameters, setLastParsedParameters] = useState<any>(null)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { setEngineeringData } = useEngineering();

  // Set initial chat state only on client
  useEffect(() => {
    const saved = localStorage.getItem('eco-draft-chat-history')
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        setMessages(parsed.map((msg: Record<string, unknown>) => ({
          ...msg,
          timestamp: new Date(msg.timestamp as string)
        })))
        return;
      } catch (e) {
        console.warn('Failed to parse saved chat history:', e)
      }
    }
    setMessages([
      {
        id: '1',
        role: 'assistant',
        content: 'Hello! I\'m your AI assistant for mechanical part design. I can help you create 2D part outlines, check manufacturability, analyze stress, and optimize designs. \n\n**Quick Examples:** \n• Create parts: *"Design an L-bracket with 6 holes"*\n• Modify parts: *"Make it 50% bigger"* or *"Increase thickness to 8mm"*\n• Custom specs: *"Create a 150mm x 100mm plate with 4 corner holes"*\n\n**Available part types:** Brackets (L, T), Gussets, Plates, Washers, Flanges, Spacers, and more!',
        timestamp: new Date(),
        actions: [
          { id: 'example-1', label: '🔧 L-Bracket', type: 'generate', payload: { description: 'Create an L-shaped bracket with mounting holes' } },
          { id: 'example-2', label: '📐 T-Bracket', type: 'generate', payload: { description: 'Create a T-shaped bracket for perpendicular mounting' } },
          { id: 'example-3', label: '🔺 Gusset', type: 'generate', payload: { description: 'Design a triangular gusset with 5mm thickness' } },
          { id: 'example-4', label: '⭕ Washer', type: 'generate', payload: { description: 'Make a washer with 20mm outer diameter and 8mm hole' } },
          { id: 'example-5', label: '🔲 Base Plate', type: 'generate', payload: { description: 'Create a rectangular base plate with corner holes' } },
          { id: 'example-6', label: '⚙️ Flange', type: 'generate', payload: { description: 'Design a circular flange with 8 bolt holes' } },
          { id: 'example-7', label: '🔨 Heavy Duty', type: 'generate', payload: { description: 'Make a heavy duty bracket with 10mm thickness from steel' } },
          { id: 'example-8', label: '✈️ Lightweight', type: 'generate', payload: { description: 'Design a lightweight aluminum bracket, 3mm thick' } }
        ]
      }
    ])
  }, []);

  // Save to localStorage whenever messages change
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('eco-draft-chat-history', JSON.stringify(messages))
    }
  }, [messages])

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollAreaRef.current) {
      // Find the viewport element within ScrollArea
      const viewport = scrollAreaRef.current.querySelector('[data-slot="scroll-area-viewport"]')
      if (viewport) {
        viewport.scrollTop = viewport.scrollHeight
      }
    }
  }, [messages])

  useEffect(() => {
    // Only run on client
    setTimeStrings(messages.map((msg) => getTimeString(msg.timestamp)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages.length]);

  const uploadDxfMutation = useMutation({
    mutationFn: (file: File) => apiClient.uploadDxf(file),
    onSuccess: (data) => {
      console.log('DXF import successful, data received:', data);
      
      const svgFile = data.files?.find((f: any) => f.format === 'svg');
      const svg = svgFile ? atob(svgFile.content_base64) : '';
      
      const formatPartType = (partType: string) => {
        let formatted = partType.replace(/^[a-z]_/, '').replace(/_/g, ' ').replace(/-/g, ' ');
        return formatted.split(' ').map(word => 
          word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
        ).join(' ');
      };
      
      const assistantMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `✅ **DXF Imported Successfully**\n\nI've imported your ${formatPartType(data.part.part_type)} design and added it to the session. The 2D outline is now displayed in the canvas.`,
        timestamp: new Date(),
        svg: svg,
        actions: [
          { id: 'check-manufacturability', label: 'Check Manufacturability', type: 'check' },
          { id: 'analyze-stress', label: 'Analyze Stress', type: 'analyze' },
          { id: 'optimize-design', label: 'Optimize Design', type: 'optimize' },
          { id: 'export-pdf', label: 'Export PDF', type: 'export' }
        ]
      }
      
      setMessages(prev => [...prev, assistantMessage])
      
      if (svg && onSvgUpdate) {
        onSvgUpdate(svg)
      }
      
      if (data.part?.geometry_data) {
        setEngineeringData({
          geometryData: data.part.geometry_data
        });
      }
      
      queryClient.invalidateQueries({ queryKey: queryKeys.sessionGraph })
      toast.success('DXF file imported successfully')
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to import DXF file')
    }
  });

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: `Uploaded DXF file: \`${file.name}\``,
      timestamp: new Date()
    }
    setMessages(prev => [...prev, userMsg])
    
    uploadDxfMutation.mutate(file);
    
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }

  const generatePartMutation = useMutation({
    mutationFn: (request: PartGenerateRequest) => apiClient.generatePart(request),
    onSuccess: (data) => {
      console.log('Part generation successful, data received:', data);
      
      // Extract SVG from files
      const svgFile = data.files?.find(f => f.format === 'svg');
      const svg = svgFile ? atob(svgFile.content_base64) : '';
      
      console.log('SVG extracted:', svg ? `${svg.substring(0, 100)}...` : 'No SVG');
      console.log('SVG file data:', svgFile);
      
      // Format the part type name properly
      const formatPartType = (partType: string) => {
        // Remove prefixes like 't_', 'l_', etc. and format nicely
        let formatted = partType.replace(/^[a-z]_/, '').replace(/_/g, ' ').replace(/-/g, ' ');
        // Capitalize each word
        formatted = formatted.split(' ').map(word => 
          word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
        ).join(' ');
        return formatted;
      };
      
      // Extract DXF
      const dxfFile = data.files?.find(f => f.format === 'dxf');

      // Add assistant response
      const assistantMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `✅ **Part Generated Successfully**\n\nI've created your ${formatPartType(data.part.part_type)} design. The 2D outline is now displayed in the canvas.\n\n**Material:** ${data.part.material}\n**Thickness:** ${data.part.thickness}mm\n**Mass:** ${data.part.mass.toFixed(3)}kg\n**Area:** ${data.part.geometry_info.area?.toFixed(1) || 'N/A'} mm²`,
        timestamp: new Date(),
        svg: svg,
        actions: [
          { id: 'check-manufacturability', label: 'Check Manufacturability', type: 'check' },
          { id: 'analyze-stress', label: 'Analyze Stress', type: 'analyze' },
          { id: 'optimize-design', label: 'Optimize Design', type: 'optimize' },
          { id: 'export-pdf', label: 'Export PDF', type: 'export' },
          { id: 'export-dxf', label: 'Download DXF', type: 'export', payload: { format: 'dxf', content: dxfFile?.content_base64 } }
        ]
      }
      setMessages(prev => [...prev, assistantMessage])

      // Update engineering context with geometry, material, thickness, etc.
      setEngineeringData({
        partType: data.part.part_type,
        geometryData: data.part.geometry_data || {},
        material: {
          name: data.part.material,
          youngs_modulus: 200000, // MPa  
          yield_strength: 250,    // MPa
          poissons_ratio: 0.3,
          density: 7850          // kg/m³
        },
        thickness: data.part.thickness,
        manufacturingProcess: 'laser_cutting', // default
        // Don't override loadCases - let the defaults from context remain
        quantity: 1,
      })
      
      // Save part context for modifications - SAVE ALL PARAMETERS!
      // We need to save the ORIGINAL parameters used to generate this part
      // This is critical for modifications to work properly
      console.log('Saving part context for future modifications');
      // The parameters should still be available from the last parsed request
      // But we should also merge any geometry info we got back
      const fullParameters = {
        ...lastParsedParameters, // Keep all original parameters
        width: data.part.geometry_info?.width || lastParsedParameters?.width || 100,
        height: data.part.geometry_info?.height || lastParsedParameters?.height || 100,
        thickness: data.part.thickness,
        material: data.part.material
      };
      console.log('Full parameters saved:', fullParameters);
      setCurrentPart(data.part.part_type, fullParameters)

      // Update canvas with SVG
      if (onSvgUpdate && svg) {
        console.log('Calling onSvgUpdate with new SVG');
        onSvgUpdate(svg)
      } else {
        console.warn('Cannot update SVG:', { hasCallback: !!onSvgUpdate, hasSvg: !!svg });
      }

      // Invalidate existing analytical queries so they fetch the newly generated geometry data
      queryClient.invalidateQueries({ queryKey: queryKeys.partAnalysis })
      queryClient.invalidateQueries({ queryKey: queryKeys.partLCA })
      queryClient.invalidateQueries({ queryKey: ['sessionGraph'] })

      toast.success('Part generated successfully!')
    },
    onError: (error) => {
      console.error('Part generation mutation error:', error);
      console.error('Error type:', typeof error);
      console.error('Error constructor:', error?.constructor?.name);
      console.error('Error keys:', Object.keys(error || {}));
      console.error('Error message:', error?.message);
      console.error('Error stringified:', JSON.stringify(error, null, 2));
      
      let errorMessage = 'An unknown error occurred';
      if (error?.message) {
        errorMessage = error.message;
      } else if (typeof error === 'string') {
        errorMessage = error;
      } else {
        errorMessage = 'Failed to generate part - please check browser console for details';
      }
      
      const chatMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `❌ **Error Generating Part**\n\n${errorMessage}\n\nPlease try rephrasing your request or provide more specific details about the part you want to create.`,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, chatMessage])
      toast.error('Failed to generate part')
    }
  })

  // Effect to handle external intents (e.g., from Pareto optimization)
  useEffect(() => {
    if (externalIntent) {
      handleSendMessage(externalIntent);
    }
  }, [externalIntent]);

  const handleSendMessage = async (customMessage?: string) => {
    const messageText = customMessage || input.trim();
    if (!messageText || generatePartMutation.isPending) return
    
    // Clear input immediately if using the input field
    if (!customMessage) {
      setInput('')
    }

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: messageText,
      timestamp: new Date()
    }
    setMessages(prev => [...prev, userMessage])
    setShowModificationHint(false)

    try {
      // Add to conversation history
      addToHistory(input.trim())
      
      // Parse the user message using NLP/LLM, appending material if set
      let promptToParse = messageText;
      if (selectedMaterial !== 'auto') {
         promptToParse += `. The material MUST be ${selectedMaterial}.`;
      }
      const parsed = await parseChatMessage(promptToParse, selectedLlm)
      
      console.log('Parsed message:', parsed);
      
      if (!parsed.part_type || !parsed.parameters) {
        throw new Error('Could not extract part type or parameters from your request.')
      }
      
      // Save the parsed parameters for later use
      setLastParsedParameters(parsed.parameters);
      
      // Update current part context
      setCurrentPart(parsed.part_type, parsed.parameters)
      
      if (parsed.action === 'checkout' && parsed.cached_data) {
        toast.success(`Checked out ${parsed.part_type} (v${parsed.cached_data.version})`)
        const svgContent = parsed.cached_data.svg ? atob(parsed.cached_data.svg) : '';
        const assistantMessage: ChatMessage = {
          id: Date.now().toString(),
          role: 'assistant',
          content: `✅ **Restored Design Version ${parsed.cached_data.version}**\n\nThe graphical parameters have been instantly checked out from the internal tree.\n\n**Material:** ${parsed.cached_data.material}\n**Thickness:** ${parsed.cached_data.thickness}mm`,
          timestamp: new Date(),
          svg: svgContent,
          actions: [
            { id: 'check-manufacturability', label: 'Check Manufacturability', type: 'check' },
            { id: 'analyze-stress', label: 'Analyze Stress', type: 'analyze' },
            { id: 'optimize-design', label: 'Optimize Design', type: 'optimize' },
            { id: 'export-pdf', label: 'Export PDF', type: 'export' }
          ]
        }
        setMessages(prev => [...prev, assistantMessage])
        
        if (onSvgUpdate && svgContent) {
          onSvgUpdate(svgContent)
        }
        
        setEngineeringData({
          partType: parsed.part_type,
          parameters: parsed.parameters,
        })
        
        queryClient.invalidateQueries({ queryKey: ['sessionGraph'] });
        return;
      }
      
      // Generate part using parsed parameters
      const requestData = {
        part_type: parsed.part_type,
        parameters: parsed.parameters,
        export_formats: ['svg', 'dxf']
      };
      console.log('Generating part with data:', requestData);
      generatePartMutation.mutate(requestData)
      
      // Store engineering data in context for downstream components
      setEngineeringData({
        partType: parsed.part_type,
        parameters: parsed.parameters,
        // geometryData, material, thickness, etc. will be set after part generation
      })
    } catch (error: any) {
      const errorMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `❌ **NLP Error**\n\n${error.message}`,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
      toast.error('Failed to understand your request')
    }
    setInput('')
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleActionClick = (action: ChatAction) => {
    if (action.type === 'generate' && action.payload) {
      // Auto-fill input for example actions
      setInput(action.payload.description as string)
    } else {
      // Trigger other actions
      if (onActionTrigger) {
        onActionTrigger(action)
      }

      // Add user message for the action
      const actionMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'user',
        content: `Triggered action: ${action.label}`,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, actionMessage])
    }
  }

  const getActionIcon = (type: ChatAction['type']) => {
    switch (type) {
      case 'generate': return <Zap className="w-4 h-4" />
      case 'check': return <CheckCircle className="w-4 h-4" />
      case 'analyze': return <BarChart3 className="w-4 h-4" />
      case 'optimize': return <Zap className="w-4 h-4" />
      case 'export': return <Download className="w-4 h-4" />
      default: return <Zap className="w-4 h-4" />
    }
  }

  const clearHistory = () => {
    const initialMessages = [{
      id: '1',
      role: 'assistant' as const,
      content: 'Hello! I\'m your AI assistant for mechanical part design. I can help you create 2D part outlines, check manufacturability, analyze stress, and optimize designs. \n\n**Quick Examples:** \n• Create parts: *"Design an L-bracket with 6 holes"*\n• Modify parts: *"Make it 50% bigger"* or *"Increase thickness to 8mm"*\n• Custom specs: *"Create a 150mm x 100mm plate with 4 corner holes"*\n\n**Available part types:** Brackets (L, T), Gussets, Plates, Washers, Flanges, Spacers, and more!',
      timestamp: new Date(),
      actions: [
        { id: 'example-1', label: '🔧 L-Bracket', type: 'generate', payload: { description: 'Create an L-shaped bracket with mounting holes' } },
        { id: 'example-2', label: '📐 T-Bracket', type: 'generate', payload: { description: 'Create a T-shaped bracket for perpendicular mounting' } },
        { id: 'example-3', label: '🔺 Gusset', type: 'generate', payload: { description: 'Design a triangular gusset with 5mm thickness' } },
        { id: 'example-4', label: '⭕ Washer', type: 'generate', payload: { description: 'Make a washer with 20mm outer diameter and 8mm hole' } },
        { id: 'example-5', label: '🔲 Base Plate', type: 'generate', payload: { description: 'Create a rectangular base plate with corner holes' } },
        { id: 'example-6', label: '⚙️ Flange', type: 'generate', payload: { description: 'Design a circular flange with 8 bolt holes' } },
        { id: 'example-7', label: '🔨 Heavy Duty', type: 'generate', payload: { description: 'Make a heavy duty bracket with 10mm thickness from steel' } },
        { id: 'example-8', label: '✈️ Lightweight', type: 'generate', payload: { description: 'Design a lightweight aluminum bracket, 3mm thick' } }
      ] as ChatAction[]
    }];
    setMessages(initialMessages);
    localStorage.removeItem('eco-draft-chat-history');
    clearConversationHistory();  // Clear NLP context
    setShowModificationHint(false);
  }
  
  // Check if input looks like a modification request
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setInput(value);
    
    // Show hint if user might be trying to modify the part
    const modKeywords = ['make it', 'bigger', 'smaller', 'thicker', 'wider', 'change', 'increase', 'decrease'];
    const hasModKeyword = modKeywords.some(kw => value.toLowerCase().includes(kw));
    const currentPart = getCurrentPart();
    setShowModificationHint(hasModKeyword && currentPart !== null);
  }

  return (
    <Card className="h-full flex flex-col overflow-hidden">
      <div className="p-4 border-b flex-shrink-0">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Design Assistant</h2>
          <Button variant="ghost" size="sm" onClick={clearHistory}>
            Clear History
          </Button>
        </div>
      </div>

      <ScrollArea className="flex-1 min-h-0" ref={scrollAreaRef}>
        <div className="p-4">
          <div className="space-y-4">
          {messages.map((message, idx) => (
            <div key={message.id} className={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className="flex-shrink-0">
                {message.role === 'user' ? (
                  <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                    <User className="w-4 h-4 text-primary-foreground" />
                  </div>
                ) : (
                  <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                    <Bot className="w-4 h-4 text-secondary-foreground" />
                  </div>
                )}
              </div>

              <div className={`flex-1 max-w-[80%] ${message.role === 'user' ? 'text-right' : ''}`}>
                <Card className={`p-3 ${message.role === 'user' ? 'bg-primary text-primary-foreground' : ''}`}>
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    <ReactMarkdown
                      components={{
                        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                        code: ({ children }) => (
                          <code className="px-1.5 py-0.5 rounded bg-muted text-muted-foreground text-xs">
                            {children}
                          </code>
                        )
                      }}
                    >
                      {message.content}
                    </ReactMarkdown>
                  </div>
                </Card>

                {message.actions && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {message.actions.map((action) => (
                      <Button
                        key={action.id}
                        variant="outline"
                        size="sm"
                        onClick={() => handleActionClick(action)}
                        className="text-xs"
                      >
                        {getActionIcon(action.type)}
                        {action.label}
                      </Button>
                    ))}
                  </div>
                )}
                <div className="text-xs text-muted-foreground mt-1">
                  {timeStrings[idx]}
                </div>
              </div>
            </div>
          ))}

          {generatePartMutation.isPending && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                <Bot className="w-4 h-4 text-secondary-foreground animate-pulse" />
              </div>
              <Card className="p-3">
                <div className="flex items-center gap-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                  <span className="text-sm text-muted-foreground">Generating your part design...</span>
                </div>
              </Card>
            </div>
          )}

          {uploadDxfMutation.isPending && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                <Bot className="w-4 h-4 text-secondary-foreground animate-pulse" />
              </div>
              <Card className="p-3">
                <div className="flex items-center gap-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                  <span className="text-sm text-muted-foreground">Importing DXF File...</span>
                </div>
              </Card>
            </div>
          )}
          </div>
        </div>
      </ScrollArea>

      <Separator />

      <div className="p-4">
        {showModificationHint && (
          <div className="mb-2 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-md text-xs text-blue-600 dark:text-blue-400">
            💡 Tip: I'll modify your current part. Try: "make it 20% bigger" or "increase thickness to 8mm"
          </div>
        )}
        
        <div className="flex gap-2">
          <select
            className="flex h-10 w-[120px] items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            value={selectedMaterial}
            onChange={(e) => setSelectedMaterial(e.target.value)}
            disabled={generatePartMutation.isPending}
          >
            <option value="auto">Auto Material</option>
            <option value="steel">Steel</option>
            <option value="aluminum">Aluminum</option>
            <option value="stainless_steel">Stainless Steel</option>
          </select>
          <select
            className="flex h-10 w-[120px] items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            value={selectedLlm}
            onChange={(e) => setSelectedLlm(e.target.value)}
            disabled={generatePartMutation.isPending}
          >
            <option value="gemini">Gemini</option>
            <option value="ollama">Ollama</option>
            <option value="openrouter">OpenRouter</option>
          </select>
          <input 
            type="file" 
            ref={fileInputRef} 
            className="hidden" 
            accept=".dxf" 
            onChange={handleFileUpload} 
          />
          <Button
            variant="outline"
            size="icon"
            onClick={() => fileInputRef.current?.click()}
            disabled={generatePartMutation.isPending || uploadDxfMutation.isPending}
            title="Upload DXF file"
          >
            <Paperclip className="w-4 h-4" />
          </Button>
          <Input
            value={input}
            onChange={handleInputChange}
            onKeyPress={handleKeyPress}
            placeholder="Describe the part you want to create..."
            disabled={generatePartMutation.isPending || uploadDxfMutation.isPending}
          />
          <Button
            onClick={() => handleSendMessage()}
            disabled={!input.trim() || generatePartMutation.isPending || uploadDxfMutation.isPending}
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </Card>
  )
}
