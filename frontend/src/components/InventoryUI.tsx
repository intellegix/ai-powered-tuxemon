// Inventory UI Component for AI-Powered Tuxemon Frontend
// Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiService as api } from '../services/api'
import { useGameData } from '../hooks/useGameStore'

interface InventoryItem {
  item_slug: string
  item_name: string
  quantity: number
  category: string
  description: string
  sprite_name: string
  can_use_now: boolean
  stack_info: string
}

interface InventoryData {
  slots: InventoryItem[]
  total_items: number
  total_slots: number
  money: number
  categories: Record<string, InventoryItem[]>
}

interface InventoryUIProps {
  isOpen: boolean
  onClose: () => void
  onUseItem?: (itemSlug: string, targetMonsterId?: string) => void
}

const CATEGORY_ICONS = {
  healing: '💊',
  capture: '⚾',
  battle: '⚔️',
  evolution: '🔮',
  misc: '📦',
  key: '🗝️'
}

const CATEGORY_COLORS = {
  healing: 'from-green-500 to-green-600',
  capture: 'from-blue-500 to-blue-600',
  battle: 'from-red-500 to-red-600',
  evolution: 'from-purple-500 to-purple-600',
  misc: 'from-gray-500 to-gray-600',
  key: 'from-yellow-500 to-yellow-600'
}

const InventoryUI: React.FC<InventoryUIProps> = ({
  isOpen,
  onClose,
  onUseItem
}) => {
  const { gameState } = useGameData()
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [selectedItem, setSelectedItem] = useState<InventoryItem | null>(null)
  const [showItemDetails, setShowItemDetails] = useState(false)
  const queryClient = useQueryClient()

  // Fetch inventory data
  const { data: inventoryData, isLoading, error } = useQuery<InventoryData>({
    queryKey: ['inventory'],
    queryFn: () => api.get('/inventory/').then(res => res.data),
    enabled: isOpen,
    staleTime: 30000, // Cache for 30 seconds
  })

  // Use item mutation
  const useItemMutation = useMutation({
    mutationFn: async ({ itemSlug, targetMonsterId }: { itemSlug: string; targetMonsterId?: string }) => {
      return api.post('/inventory/use', {
        item_slug: itemSlug,
        target_monster_id: targetMonsterId,
        quantity: 1
      })
    },
    onSuccess: (data) => {
      // Refresh inventory data
      queryClient.invalidateQueries({ queryKey: ['inventory'] })

      // Show success message
      console.log('Item used successfully:', data.data.message)

      // Call parent handler
      if (onUseItem) {
        onUseItem(selectedItem?.item_slug || '')
      }

      setShowItemDetails(false)
      setSelectedItem(null)
    },
    onError: (error: any) => {
      console.error('Failed to use item:', error.response?.data?.detail || error.message)
    }
  })

  const categories = React.useMemo(() => {
    if (!inventoryData) return []

    const cats = ['all', ...Object.keys(inventoryData.categories)]
    return cats
  }, [inventoryData])

  const filteredItems = React.useMemo(() => {
    if (!inventoryData) return []

    if (selectedCategory === 'all') {
      return inventoryData.slots
    }

    return inventoryData.categories[selectedCategory] || []
  }, [inventoryData, selectedCategory])

  const handleItemClick = (item: InventoryItem) => {
    setSelectedItem(item)
    setShowItemDetails(true)
  }

  const handleUseItem = () => {
    if (!selectedItem) return

    // For items that need a target monster, we'd show monster selection
    // For now, just use the first monster in the party
    let targetMonsterId: string | undefined = undefined

    if (selectedItem.category === 'healing' && gameState?.party?.length > 0) {
      targetMonsterId = gameState.party[0].id
    }

    useItemMutation.mutate({
      itemSlug: selectedItem.item_slug,
      targetMonsterId
    })
  }

  if (!isOpen) return null

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-gradient-to-br from-gray-900 via-purple-900 to-blue-900 rounded-2xl border border-purple-500/30 shadow-2xl w-full max-w-md max-h-[90vh] flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-purple-500/30">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-500 rounded-lg flex items-center justify-center">
              🎒
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Inventory</h2>
              <p className="text-purple-300 text-sm">
                {inventoryData?.total_items || 0} items • ${inventoryData?.money || 0}
              </p>
            </div>
          </div>

          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={onClose}
            className="text-purple-300 hover:text-white text-2xl"
          >
            ✕
          </motion.button>
        </div>

        {/* Category Tabs */}
        <div className="p-4 border-b border-purple-500/20">
          <div className="flex space-x-2 overflow-x-auto">
            {categories.map((category) => (
              <motion.button
                key={category}
                whileTap={{ scale: 0.95 }}
                onClick={() => setSelectedCategory(category)}
                className={`flex-shrink-0 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  selectedCategory === category
                    ? 'bg-purple-500 text-white'
                    : 'bg-purple-500/20 text-purple-300 hover:bg-purple-500/30'
                }`}
              >
                {category === 'all' ? '📋' : CATEGORY_ICONS[category as keyof typeof CATEGORY_ICONS] || '📦'}{' '}
                {category === 'all' ? 'All' : category.charAt(0).toUpperCase() + category.slice(1)}
              </motion.button>
            ))}
          </div>
        </div>

        {/* Items Grid */}
        <div className="flex-1 p-4 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center h-40">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full"
              />
            </div>
          ) : error ? (
            <div className="text-center text-red-400 py-8">
              Failed to load inventory
            </div>
          ) : filteredItems.length === 0 ? (
            <div className="text-center text-purple-300 py-8">
              <div className="text-4xl mb-2">📦</div>
              <p>No items in this category</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {filteredItems.map((item, index) => (
                <motion.div
                  key={item.item_slug}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  onClick={() => handleItemClick(item)}
                  className={`bg-gradient-to-br ${
                    CATEGORY_COLORS[item.category as keyof typeof CATEGORY_COLORS] || 'from-gray-500 to-gray-600'
                  } p-4 rounded-xl border border-white/20 cursor-pointer hover:scale-105 transition-transform`}
                >
                  <div className="text-center">
                    {/* Item Icon */}
                    <div className="w-12 h-12 bg-white/20 rounded-lg mx-auto mb-2 flex items-center justify-center text-2xl">
                      {CATEGORY_ICONS[item.category as keyof typeof CATEGORY_ICONS] || '📦'}
                    </div>

                    {/* Item Name */}
                    <h3 className="text-white font-medium text-sm mb-1 truncate">
                      {item.item_name}
                    </h3>

                    {/* Quantity */}
                    <p className="text-white/80 text-xs">
                      x{item.quantity}
                    </p>

                    {/* Use indicator */}
                    {item.can_use_now && (
                      <div className="w-2 h-2 bg-green-400 rounded-full mx-auto mt-1" />
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>

        {/* Stats Bar */}
        <div className="p-4 border-t border-purple-500/20 bg-purple-900/30">
          <div className="flex items-center justify-between text-sm text-purple-300">
            <span>{inventoryData?.total_items || 0}/{inventoryData?.total_slots || 50} items</span>
            <span>💰 ${inventoryData?.money || 0}</span>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-purple-900/50 rounded-full h-2 mt-2">
            <div
              className="bg-gradient-to-r from-purple-500 to-blue-500 h-2 rounded-full transition-all duration-300"
              style={{
                width: `${Math.min(100, ((inventoryData?.total_items || 0) / (inventoryData?.total_slots || 50)) * 100)}%`
              }}
            />
          </div>
        </div>
      </motion.div>

      {/* Item Details Modal */}
      <AnimatePresence>
        {showItemDetails && selectedItem && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="absolute inset-0 flex items-center justify-center z-10"
            onClick={() => setShowItemDetails(false)}
          >
            <motion.div
              onClick={(e) => e.stopPropagation()}
              className="bg-gray-900 border border-purple-500/30 rounded-xl p-6 m-4 max-w-sm w-full"
            >
              <div className="text-center mb-4">
                <div className={`w-16 h-16 bg-gradient-to-br ${
                  CATEGORY_COLORS[selectedItem.category as keyof typeof CATEGORY_COLORS]
                } rounded-xl mx-auto mb-3 flex items-center justify-center text-3xl`}>
                  {CATEGORY_ICONS[selectedItem.category as keyof typeof CATEGORY_ICONS]}
                </div>

                <h3 className="text-xl font-bold text-white mb-1">
                  {selectedItem.item_name}
                </h3>

                <p className="text-purple-300 text-sm mb-3">
                  {selectedItem.description}
                </p>

                <div className="flex items-center justify-center space-x-4 text-sm text-purple-300">
                  <span>Quantity: {selectedItem.quantity}</span>
                  <span>•</span>
                  <span>{selectedItem.stack_info}</span>
                </div>
              </div>

              <div className="flex space-x-3">
                <motion.button
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setShowItemDetails(false)}
                  className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-white text-sm font-medium transition-colors"
                >
                  Cancel
                </motion.button>

                {selectedItem.can_use_now && (
                  <motion.button
                    whileTap={{ scale: 0.95 }}
                    onClick={handleUseItem}
                    disabled={useItemMutation.isPending}
                    className="flex-1 px-4 py-2 bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 rounded-lg text-white text-sm font-medium transition-colors disabled:opacity-50"
                  >
                    {useItemMutation.isPending ? 'Using...' : 'Use Item'}
                  </motion.button>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default InventoryUI