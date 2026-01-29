// Game Canvas Component for AI-Powered Tuxemon Frontend
// Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import React, { useRef, useEffect, useCallback, useState } from 'react'
import { useGameData, useUI } from '../hooks/useGameStore'
import { useWebSocket } from '../services/websocket'
import type { NPC, InteractiveObject, TouchPosition } from '../types/game'

interface GameCanvasProps {
  width: number
  height: number
}

interface Sprite {
  image: HTMLImageElement
  loaded: boolean
}

export const GameCanvas: React.FC<GameCanvasProps> = ({ width, height }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const contextRef = useRef<CanvasRenderingContext2D | null>(null)
  const animationFrameRef = useRef<number>()

  const { gameState, worldState } = useGameData()
  const { ui, setLoading, setError } = useUI()
  const { sendPlayerUpdate } = useWebSocket()

  // Game rendering state
  const [sprites, setSprites] = useState<Map<string, Sprite>>(new Map())
  const [cameraOffset, setCameraOffset] = useState({ x: 0, y: 0 })
  const [lastRenderTime, setLastRenderTime] = useState(0)

  // Touch handling state
  const [touchStart, setTouchStart] = useState<TouchPosition | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  // Constants
  const TILE_SIZE = 32
  const PLAYER_SPEED = 4
  const CAMERA_SMOOTH = 0.1

  // Initialize canvas and context
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const context = canvas.getContext('2d')
    if (!context) return

    contextRef.current = context

    // Set up canvas for high DPI displays
    const dpr = window.devicePixelRatio || 1
    canvas.width = width * dpr
    canvas.height = height * dpr
    canvas.style.width = `${width}px`
    canvas.style.height = `${height}px`
    context.scale(dpr, dpr)

    // Configure rendering settings
    context.imageSmoothingEnabled = false // Pixel-perfect sprites
    context.textAlign = 'center'
    context.textBaseline = 'middle'

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
    }
  }, [width, height])

  // Load sprites
  const loadSprite = useCallback(async (spriteName: string, url: string): Promise<HTMLImageElement> => {
    return new Promise((resolve, reject) => {
      const image = new Image()
      image.onload = () => {
        setSprites(prev => new Map(prev.set(spriteName, { image, loaded: true })))
        resolve(image)
      }
      image.onerror = () => {
        console.error(`Failed to load sprite: ${spriteName}`)
        reject(new Error(`Failed to load sprite: ${spriteName}`))
      }
      image.src = url
    })
  }, [])

  // Load essential sprites
  useEffect(() => {
    const loadEssentialSprites = async () => {
      try {
        setLoading(true)

        const spritesToLoad = [
          { name: 'player', url: '/sprites/player/trainer_front.png' },
          { name: 'grass', url: '/sprites/tiles/grass.png' },
          { name: 'dirt', url: '/sprites/tiles/dirt.png' },
          { name: 'water', url: '/sprites/tiles/water.png' },
        ]

        await Promise.all(
          spritesToLoad.map(sprite => loadSprite(sprite.name, sprite.url))
        )

        console.log('✅ Essential sprites loaded')
      } catch (error) {
        console.error('❌ Failed to load sprites:', error)
        setError('Failed to load game graphics')
      } finally {
        setLoading(false)
      }
    }

    loadEssentialSprites()
  }, [loadSprite, setLoading, setError])

  // Update camera position to follow player
  useEffect(() => {
    if (!gameState) return

    const [playerX, playerY] = gameState.position
    const targetX = (width / 2) - (playerX * TILE_SIZE)
    const targetY = (height / 2) - (playerY * TILE_SIZE)

    setCameraOffset(prev => ({
      x: prev.x + (targetX - prev.x) * CAMERA_SMOOTH,
      y: prev.y + (targetY - prev.y) * CAMERA_SMOOTH,
    }))
  }, [gameState?.position, width, height])

  // Render game world
  const render = useCallback((timestamp: number) => {
    const context = contextRef.current
    const canvas = canvasRef.current
    if (!context || !canvas || !gameState || !worldState) return

    // Calculate delta time
    const deltaTime = timestamp - lastRenderTime
    setLastRenderTime(timestamp)

    // Clear canvas
    context.clearRect(0, 0, width, height)

    // Save context for camera transform
    context.save()
    context.translate(cameraOffset.x, cameraOffset.y)

    // Render map tiles (simplified - in real implementation, load from TMX)
    renderMap(context)

    // Render NPCs
    worldState.npcsNearby.forEach(npc => {
      renderNPC(context, npc)
    })

    // Render player
    if (gameState.position) {
      const [playerX, playerY] = gameState.position
      renderPlayer(context, playerX, playerY)
    }

    // Render interactive objects
    worldState.interactiveObjects?.forEach(obj => {
      renderInteractiveObject(context, obj)
    })

    // Restore context
    context.restore()

    // Render UI elements (HUD, minimap, etc.)
    renderUI(context, deltaTime)

    // Schedule next frame
    animationFrameRef.current = requestAnimationFrame(render)
  }, [gameState, worldState, cameraOffset, width, height, lastRenderTime])

  // Start render loop
  useEffect(() => {
    if (gameState && worldState) {
      animationFrameRef.current = requestAnimationFrame(render)
    }

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
    }
  }, [gameState, worldState, render])

  // Rendering functions
  const renderMap = (context: CanvasRenderingContext2D) => {
    // Simplified map rendering - draw a grid of grass tiles
    const grassSprite = sprites.get('grass')?.image
    if (!grassSprite) return

    const startX = Math.floor(-cameraOffset.x / TILE_SIZE) - 1
    const startY = Math.floor(-cameraOffset.y / TILE_SIZE) - 1
    const endX = startX + Math.ceil(width / TILE_SIZE) + 2
    const endY = startY + Math.ceil(height / TILE_SIZE) + 2

    for (let x = startX; x < endX; x++) {
      for (let y = startY; y < endY; y++) {
        context.drawImage(grassSprite, x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
      }
    }
  }

  const renderPlayer = (context: CanvasRenderingContext2D, x: number, y: number) => {
    const playerSprite = sprites.get('player')?.image
    if (!playerSprite) {
      // Fallback: draw a colored rectangle
      context.fillStyle = '#4f46e5'
      context.fillRect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
      return
    }

    context.drawImage(playerSprite, x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)

    // Player name label
    context.fillStyle = 'white'
    context.strokeStyle = 'black'
    context.lineWidth = 2
    context.font = '12px monospace'
    const nameY = y * TILE_SIZE - 5
    context.strokeText(gameState?.playerId.substring(0, 8) || 'Player', (x + 0.5) * TILE_SIZE, nameY)
    context.fillText(gameState?.playerId.substring(0, 8) || 'Player', (x + 0.5) * TILE_SIZE, nameY)
  }

  const renderNPC = (context: CanvasRenderingContext2D, npc: NPC) => {
    const [npcX, npcY] = npc.position

    // Try to load NPC sprite dynamically
    const spriteName = `npc_${npc.spriteName}`
    let npcSprite = sprites.get(spriteName)?.image

    if (!npcSprite) {
      // Load sprite if not already loaded
      loadSprite(spriteName, `/sprites/npcs/${npc.spriteName}.png`).catch(() => {
        // Sprite loading failed, will use fallback
      })

      // Fallback: draw a colored rectangle
      const color = npc.canBattle ? '#ef4444' : npc.isTrainer ? '#f59e0b' : '#10b981'
      context.fillStyle = color
      context.fillRect(npcX * TILE_SIZE, npcY * TILE_SIZE, TILE_SIZE, TILE_SIZE)
    } else {
      context.drawImage(npcSprite, npcX * TILE_SIZE, npcY * TILE_SIZE, TILE_SIZE, TILE_SIZE)
    }

    // NPC name and relationship indicator
    context.fillStyle = 'white'
    context.strokeStyle = 'black'
    context.lineWidth = 2
    context.font = '10px monospace'
    const nameY = npcY * TILE_SIZE - 5
    context.strokeText(npc.name, (npcX + 0.5) * TILE_SIZE, nameY)
    context.fillText(npc.name, (npcX + 0.5) * TILE_SIZE, nameY)

    // Relationship level indicator (hearts)
    if (npc.relationshipLevel > 0.3) {
      const hearts = Math.ceil(npc.relationshipLevel * 3)
      context.fillStyle = '#ef4444'
      for (let i = 0; i < hearts; i++) {
        context.fillText('♥', (npcX + 0.5) * TILE_SIZE + (i - 1) * 8, nameY - 12)
      }
    }

    // Interaction indicator
    if (npc.approachable) {
      const distance = Math.abs(npcX - (gameState?.position[0] || 0)) + Math.abs(npcY - (gameState?.position[1] || 0))
      if (distance <= 1) {
        // Show interaction prompt
        context.fillStyle = 'rgba(255, 255, 255, 0.9)'
        context.strokeStyle = 'black'
        context.lineWidth = 1
        context.font = '8px monospace'
        const promptY = npcY * TILE_SIZE + TILE_SIZE + 15
        context.strokeText('Press to talk', (npcX + 0.5) * TILE_SIZE, promptY)
        context.fillText('Press to talk', (npcX + 0.5) * TILE_SIZE, promptY)
      }
    }
  }

  const renderInteractiveObject = (context: CanvasRenderingContext2D, obj: InteractiveObject) => {
    const [objX, objY] = obj.position

    // Simplified object rendering
    context.fillStyle = obj.type === 'chest' ? '#8b4513' : obj.type === 'sign' ? '#d2691e' : '#666'
    context.fillRect(objX * TILE_SIZE, objY * TILE_SIZE, TILE_SIZE, TILE_SIZE)

    // Object label
    context.fillStyle = 'white'
    context.strokeStyle = 'black'
    context.lineWidth = 1
    context.font = '8px monospace'
    context.strokeText(obj.type, (objX + 0.5) * TILE_SIZE, objY * TILE_SIZE - 5)
    context.fillText(obj.type, (objX + 0.5) * TILE_SIZE, objY * TILE_SIZE - 5)
  }

  const renderUI = (context: CanvasRenderingContext2D, deltaTime: number) => {
    // Connection status indicator
    const connectionColor = worldState ? '#10b981' : '#ef4444'
    context.fillStyle = connectionColor
    context.fillRect(width - 20, 10, 10, 10)

    // FPS counter (debug)
    if (ui.loading || deltaTime > 0) {
      const fps = deltaTime > 0 ? Math.round(1000 / deltaTime) : 0
      context.fillStyle = 'white'
      context.strokeStyle = 'black'
      context.lineWidth = 1
      context.font = '10px monospace'
      context.strokeText(`FPS: ${fps}`, 50, 20)
      context.fillText(`FPS: ${fps}`, 50, 20)
    }

    // Player position (debug)
    if (gameState?.position) {
      const [x, y] = gameState.position
      context.strokeText(`Pos: ${x}, ${y}`, 50, 35)
      context.fillText(`Pos: ${x}, ${y}`, 50, 35)
    }
  }

  // Touch handling
  const handleTouchStart = (event: React.TouchEvent) => {
    event.preventDefault()
    const touch = event.touches[0]
    const rect = canvasRef.current?.getBoundingClientRect()
    if (!rect) return

    setTouchStart({
      x: touch.clientX - rect.left,
      y: touch.clientY - rect.top,
      timestamp: Date.now(),
    })
  }

  const handleTouchMove = (event: React.TouchEvent) => {
    event.preventDefault()
    if (!touchStart || !gameState) return

    const touch = event.touches[0]
    const rect = canvasRef.current?.getBoundingClientRect()
    if (!rect) return

    const currentPos = {
      x: touch.clientX - rect.left,
      y: touch.clientY - rect.top,
      timestamp: Date.now(),
    }

    const deltaX = currentPos.x - touchStart.x
    const deltaY = currentPos.y - touchStart.y
    const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY)

    if (distance > 10) {
      setIsDragging(true)
      // TODO: Implement camera panning for large movements
    }
  }

  const handleTouchEnd = (event: React.TouchEvent) => {
    event.preventDefault()
    if (!touchStart || !gameState) return

    const touch = event.changedTouches[0]
    const rect = canvasRef.current?.getBoundingClientRect()
    if (!rect) return

    const endPos = {
      x: touch.clientX - rect.left,
      y: touch.clientY - rect.top,
      timestamp: Date.now(),
    }

    const deltaX = endPos.x - touchStart.x
    const deltaY = endPos.y - touchStart.y
    const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY)
    const duration = endPos.timestamp - touchStart.timestamp

    // Handle different gesture types
    if (!isDragging && distance < 10 && duration < 500) {
      // Tap gesture - move player or interact
      handleTap(endPos.x, endPos.y)
    } else if (distance > 50 && duration < 300) {
      // Swipe gesture - quick movement
      handleSwipe(deltaX, deltaY)
    }

    // Reset touch state
    setTouchStart(null)
    setIsDragging(false)
  }

  const handleTap = (x: number, y: number) => {
    if (!gameState) return

    // Convert screen coordinates to world coordinates
    const worldX = Math.floor((x - cameraOffset.x) / TILE_SIZE)
    const worldY = Math.floor((y - cameraOffset.y) / TILE_SIZE)

    // Check if tapping on an NPC
    const tappedNPC = worldState?.npcsNearby.find(npc => {
      const [npcX, npcY] = npc.position
      return npcX === worldX && npcY === worldY
    })

    if (tappedNPC && tappedNPC.approachable) {
      // Interact with NPC
      const distance = Math.abs(worldX - gameState.position[0]) + Math.abs(worldY - gameState.position[1])
      if (distance <= 1) {
        handleNPCInteraction(tappedNPC)
      }
    } else {
      // Move player to tapped location (simplified pathfinding)
      const [currentX, currentY] = gameState.position
      const distance = Math.abs(worldX - currentX) + Math.abs(worldY - currentY)

      if (distance === 1) {
        // Direct adjacent movement
        movePlayer(worldX, worldY)
      }
    }
  }

  const handleSwipe = (deltaX: number, deltaY: number) => {
    if (!gameState) return

    const [currentX, currentY] = gameState.position
    let newX = currentX
    let newY = currentY

    // Determine swipe direction
    if (Math.abs(deltaX) > Math.abs(deltaY)) {
      // Horizontal swipe
      newX += deltaX > 0 ? 1 : -1
    } else {
      // Vertical swipe
      newY += deltaY > 0 ? 1 : -1
    }

    movePlayer(newX, newY)
  }

  const movePlayer = async (newX: number, newY: number) => {
    if (!gameState) return

    try {
      // TODO: Add movement validation and collision detection
      // For now, allow all movements

      // Update local state immediately for responsiveness
      const newGameState = {
        ...gameState,
        position: [newX, newY] as [number, number],
      }
      useGameData.getState().setGameState(newGameState)

      // Send update to server
      sendPlayerUpdate()
    } catch (error) {
      console.error('Movement failed:', error)
      setError('Failed to move player')
    }
  }

  const handleNPCInteraction = async (npc: NPC) => {
    try {
      // TODO: Implement NPC interaction through API
      console.log('Interacting with NPC:', npc.name)

      // Show interaction UI
      setError(null) // Clear any previous errors
    } catch (error) {
      console.error('NPC interaction failed:', error)
      setError('Failed to interact with NPC')
    }
  }

  return (
    <canvas
      ref={canvasRef}
      style={{
        display: 'block',
        touchAction: 'none', // Prevent default touch behaviors
        userSelect: 'none',
      }}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    />
  )
}

export default GameCanvas