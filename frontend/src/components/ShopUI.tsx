// Shop UI Component for AI-Powered Tuxemon Frontend
// Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiService as api } from '../services/api'
import { useGameData } from '../hooks/useGameStore'

interface ShopItem {
  item_slug: string
  item_name: string
  description: string
  category: string
  sprite_name: string
  current_price: number
  base_price: number
  price_modifier: number
  current_stock: number
  max_stock: number
  in_stock: boolean
  price_trend: 'rising' | 'falling' | 'stable'
  demand_level: 'low' | 'medium' | 'high'
  popularity: number
}

interface ShopData {
  npc_id: string
  npc_name: string
  shop_type: string
  items: ShopItem[]
  total_items: number
  accepts_selling: boolean
  buy_back_rate: number
}

interface ShopUIProps {
  isOpen: boolean
  npcId: string
  npcName: string
  onClose: () => void
}

const CATEGORY_ICONS = {
  healing: '💊',
  capture: '⚾',
  battle: '⚔️',
  evolution: '🔮',
  misc: '📦',
  key: '🗝️'
}

const TREND_INDICATORS = {
  rising: '📈',
  falling: '📉',
  stable: '➡️'
}

const DEMAND_COLORS = {
  low: 'text-gray-400',
  medium: 'text-yellow-400',
  high: 'text-red-400'
}

const ShopUI: React.FC<ShopUIProps> = ({
  isOpen,
  npcId,
  npcName,
  onClose
}) => {
  const { gameState, refreshGameData } = useGameData()
  const [activeTab, setActiveTab] = useState<'buy' | 'sell'>('buy')
  const [selectedItem, setSelectedItem] = useState<ShopItem | null>(null)
  const [quantity, setQuantity] = useState(1)
  const [showConfirmation, setShowConfirmation] = useState(false)
  const queryClient = useQueryClient()

  // Fetch shop data
  const { data: shopData, isLoading, error } = useQuery<ShopData>({
    queryKey: ['shop', npcId],
    queryFn: () => api.get(`/shop/${npcId}`).then(res => res.data),
    enabled: isOpen && !!npcId,
    staleTime: 60000, // Cache for 1 minute
  })

  // Purchase mutation
  const purchaseMutation = useMutation({
    mutationFn: async ({ itemSlug, quantity }: { itemSlug: string; quantity: number }) => {
      return api.post(`/shop/${npcId}/purchase`, {
        item_slug: itemSlug,
        quantity
      })
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['shop', npcId] })
      queryClient.invalidateQueries({ queryKey: ['inventory'] })
      refreshGameData()
      setShowConfirmation(false)
      setSelectedItem(null)
      console.log('Purchase successful:', data.data.message)
    },
    onError: (error: any) => {
      console.error('Purchase failed:', error.response?.data?.detail || error.message)
    }
  })

  // Sell mutation
  const sellMutation = useMutation({
    mutationFn: async ({ itemSlug, quantity }: { itemSlug: string; quantity: number }) => {
      return api.post(`/shop/${npcId}/sell`, {
        item_slug: itemSlug,
        quantity
      })
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['shop', npcId] })
      queryClient.invalidateQueries({ queryKey: ['inventory'] })
      refreshGameData()
      setShowConfirmation(false)
      setSelectedItem(null)
      console.log('Sale successful:', data.data.message)
    },
    onError: (error: any) => {
      console.error('Sale failed:', error.response?.data?.detail || error.message)
    }
  })

  const handleItemClick = (item: ShopItem) => {
    setSelectedItem(item)
    setQuantity(1)
    setShowConfirmation(true)
  }

  const handleTransaction = () => {
    if (!selectedItem) return

    if (activeTab === 'buy') {
      purchaseMutation.mutate({
        itemSlug: selectedItem.item_slug,
        quantity
      })
    } else {
      sellMutation.mutate({
        itemSlug: selectedItem.item_slug,
        quantity
      })
    }
  }

  const getItemsToDisplay = () => {
    if (activeTab === 'buy') {
      return shopData?.items || []
    } else {
      // For selling, show player inventory items that this shop accepts
      return gameState?.inventory?.filter(item =>
        shopData?.accepts_selling
      ) || []
    }
  }

  const getTotalCost = () => {
    if (!selectedItem) return 0
    if (activeTab === 'buy') {
      return selectedItem.current_price * quantity
    } else {
      // Calculate sell price (simplified)
      return Math.floor(selectedItem.current_price * (shopData?.buy_back_rate || 0.5)) * quantity
    }
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
        className="bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 rounded-2xl border border-blue-500/30 shadow-2xl w-full max-w-md max-h-[90vh] flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-blue-500/30">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-500 rounded-lg flex items-center justify-center">
              🏪
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">{npcName}'s Shop</h2>
              <p className="text-blue-300 text-sm">
                {shopData?.total_items || 0} items • ${gameState?.money || 0}
              </p>
            </div>
          </div>

          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={onClose}
            className="text-blue-300 hover:text-white text-2xl"
          >
            ✕
          </motion.button>
        </div>

        {/* Tab Navigation */}
        <div className="p-4 border-b border-blue-500/20">
          <div className="flex bg-blue-900/30 rounded-lg p-1">
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={() => setActiveTab('buy')}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'buy'
                  ? 'bg-blue-500 text-white'
                  : 'text-blue-300 hover:text-white'
              }`}
            >
              🛒 Buy
            </motion.button>
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={() => setActiveTab('sell')}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'sell'
                  ? 'bg-blue-500 text-white'
                  : 'text-blue-300 hover:text-white'
              }`}
            >
              💰 Sell
            </motion.button>
          </div>
        </div>

        {/* Items List */}
        <div className="flex-1 p-4 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center h-40">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full"
              />
            </div>
          ) : error ? (
            <div className="text-center text-red-400 py-8">
              Failed to load shop data
            </div>
          ) : getItemsToDisplay().length === 0 ? (
            <div className="text-center text-blue-300 py-8">
              <div className="text-4xl mb-2">
                {activeTab === 'buy' ? '🛒' : '💰'}
              </div>
              <p>
                {activeTab === 'buy'
                  ? 'No items available for purchase'
                  : 'No items to sell'
                }
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {getItemsToDisplay().map((item, index) => {
                const isShopItem = 'price_trend' in item

                return (
                  <motion.div
                    key={item.item_slug}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    onClick={() => handleItemClick(item as ShopItem)}
                    className="bg-gradient-to-r from-blue-800/50 to-purple-800/50 p-4 rounded-xl border border-blue-500/20 cursor-pointer hover:scale-102 transition-transform"
                  >
                    <div className="flex items-center space-x-3">
                      {/* Item Icon */}
                      <div className="w-12 h-12 bg-blue-500/30 rounded-lg flex items-center justify-center text-xl">
                        {CATEGORY_ICONS[item.category as keyof typeof CATEGORY_ICONS] || '📦'}
                      </div>

                      {/* Item Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between">
                          <div>
                            <h3 className="text-white font-medium text-sm truncate">
                              {item.item_name}
                            </h3>
                            <p className="text-blue-300 text-xs truncate">
                              {item.description}
                            </p>
                          </div>

                          <div className="text-right ml-2">
                            <div className="text-white font-bold">
                              ${isShopItem ? (item as ShopItem).current_price :
                                Math.floor(((item as any).current_price || 100) * (shopData?.buy_back_rate || 0.5))}
                            </div>
                            {isShopItem && (
                              <div className="flex items-center space-x-1 text-xs">
                                <span className={DEMAND_COLORS[(item as ShopItem).demand_level]}>
                                  {TREND_INDICATORS[(item as ShopItem).price_trend]}
                                </span>
                                <span className="text-blue-300">
                                  {(item as ShopItem).current_stock}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Stock/Quantity Info */}
                        <div className="flex items-center justify-between mt-2 text-xs text-blue-300">
                          {activeTab === 'buy' ? (
                            <>
                              <span>
                                Stock: {(item as ShopItem).current_stock}/{(item as ShopItem).max_stock}
                              </span>
                              {!(item as ShopItem).in_stock && (
                                <span className="text-red-400">Out of Stock</span>
                              )}
                            </>
                          ) : (
                            <span>You have: {(item as any).quantity || 0}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )
              })}
            </div>
          )}
        </div>

        {/* Shop Info */}
        <div className="p-4 border-t border-blue-500/20 bg-blue-900/30">
          <div className="flex items-center justify-between text-sm text-blue-300">
            <span>Your Money: ${gameState?.money || 0}</span>
            {shopData?.accepts_selling && activeTab === 'sell' && (
              <span>Buy-back Rate: {Math.round((shopData.buy_back_rate || 0.5) * 100)}%</span>
            )}
          </div>
        </div>
      </motion.div>

      {/* Transaction Confirmation Modal */}
      <AnimatePresence>
        {showConfirmation && selectedItem && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="absolute inset-0 flex items-center justify-center z-10"
            onClick={() => setShowConfirmation(false)}
          >
            <motion.div
              onClick={(e) => e.stopPropagation()}
              className="bg-gray-900 border border-blue-500/30 rounded-xl p-6 m-4 max-w-sm w-full"
            >
              <div className="text-center mb-4">
                <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-500 rounded-xl mx-auto mb-3 flex items-center justify-center text-3xl">
                  {CATEGORY_ICONS[selectedItem.category as keyof typeof CATEGORY_ICONS]}
                </div>

                <h3 className="text-xl font-bold text-white mb-1">
                  {activeTab === 'buy' ? 'Purchase' : 'Sell'} {selectedItem.item_name}
                </h3>

                <p className="text-blue-300 text-sm mb-4">
                  {selectedItem.description}
                </p>

                {/* Quantity Selector */}
                <div className="flex items-center justify-center space-x-3 mb-4">
                  <motion.button
                    whileTap={{ scale: 0.9 }}
                    onClick={() => setQuantity(Math.max(1, quantity - 1))}
                    className="w-8 h-8 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-bold"
                  >
                    -
                  </motion.button>

                  <div className="px-4 py-2 bg-gray-800 rounded-lg text-white font-medium min-w-[60px] text-center">
                    {quantity}
                  </div>

                  <motion.button
                    whileTap={{ scale: 0.9 }}
                    onClick={() => {
                      const maxQty = activeTab === 'buy'
                        ? Math.min(10, selectedItem.current_stock)
                        : Math.min(10, (selectedItem as any).quantity || 1)
                      setQuantity(Math.min(maxQty, quantity + 1))
                    }}
                    className="w-8 h-8 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-bold"
                  >
                    +
                  </motion.button>
                </div>

                {/* Total Cost */}
                <div className="text-center mb-4">
                  <div className="text-2xl font-bold text-white">
                    {activeTab === 'buy' ? '-' : '+'}${getTotalCost()}
                  </div>
                  <div className="text-blue-300 text-sm">
                    ${getTotalCost() / quantity} per item
                  </div>
                </div>
              </div>

              <div className="flex space-x-3">
                <motion.button
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setShowConfirmation(false)}
                  className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-white text-sm font-medium transition-colors"
                >
                  Cancel
                </motion.button>

                <motion.button
                  whileTap={{ scale: 0.95 }}
                  onClick={handleTransaction}
                  disabled={purchaseMutation.isPending || sellMutation.isPending}
                  className="flex-1 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 rounded-lg text-white text-sm font-medium transition-colors disabled:opacity-50"
                >
                  {(purchaseMutation.isPending || sellMutation.isPending)
                    ? 'Processing...'
                    : activeTab === 'buy' ? 'Purchase' : 'Sell'
                  }
                </motion.button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default ShopUI