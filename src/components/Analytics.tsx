import React from 'react'
import { motion } from 'framer-motion'
import { TrendingUp, Users, Heart, Share, Eye, MessageCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Progress } from './ui/progress'

const analyticsData = {
  overview: {
    totalReach: 125000,
    totalEngagement: 8500,
    totalFollowers: 45000,
    growthRate: 12.5
  },
  platforms: [
    {
      name: 'TikTok',
      icon: '🎵',
      followers: 18500,
      engagement: 3200,
      reach: 45000,
      growth: 15.2,
      color: 'text-pink-600'
    },
    {
      name: 'Instagram',
      icon: '📸',
      followers: 12000,
      engagement: 2100,
      reach: 32000,
      growth: 8.7,
      color: 'text-purple-600'
    },
    {
      name: 'Facebook',
      icon: '📘',
      followers: 8500,
      engagement: 1800,
      reach: 28000,
      growth: 5.3,
      color: 'text-blue-600'
    },
    {
      name: 'YouTube',
      icon: '📺',
      followers: 6000,
      engagement: 1400,
      reach: 20000,
      growth: 22.1,
      color: 'text-red-600'
    }
  ],
  topPosts: [
    {
      id: 1,
      title: 'Morning Routine Tips',
      platform: 'TikTok',
      views: 25000,
      likes: 1200,
      shares: 340,
      comments: 89
    },
    {
      id: 2,
      title: 'Behind the Scenes',
      platform: 'Instagram',
      views: 18000,
      likes: 890,
      shares: 156,
      comments: 67
    },
    {
      id: 3,
      title: 'Product Review',
      platform: 'YouTube',
      views: 12000,
      likes: 567,
      shares: 89,
      comments: 123
    }
  ]
}

export function Analytics() {
  const formatNumber = (num: number) => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M'
    }
    if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K'
    }
    return num.toString()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-slate-800">Analytics Dashboard</h2>
        <p className="text-slate-600">Track your social media performance across all platforms</p>
      </div>

      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600">Total Reach</p>
                  <p className="text-2xl font-bold text-slate-800">
                    {formatNumber(analyticsData.overview.totalReach)}
                  </p>
                </div>
                <Eye className="w-8 h-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600">Engagement</p>
                  <p className="text-2xl font-bold text-slate-800">
                    {formatNumber(analyticsData.overview.totalEngagement)}
                  </p>
                </div>
                <Heart className="w-8 h-8 text-red-500" />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
        >
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600">Followers</p>
                  <p className="text-2xl font-bold text-slate-800">
                    {formatNumber(analyticsData.overview.totalFollowers)}
                  </p>
                </div>
                <Users className="w-8 h-8 text-green-500" />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.3 }}
        >
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600">Growth Rate</p>
                  <p className="text-2xl font-bold text-slate-800">
                    +{analyticsData.overview.growthRate}%
                  </p>
                </div>
                <TrendingUp className="w-8 h-8 text-purple-500" />
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Platform Performance */}
        <Card>
          <CardHeader>
            <CardTitle>Platform Performance</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {analyticsData.platforms.map((platform, index) => (
              <motion.div
                key={platform.name}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
                className="flex items-center justify-between p-4 bg-slate-50 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <div className="text-2xl">{platform.icon}</div>
                  <div>
                    <h4 className={`font-semibold ${platform.color}`}>
                      {platform.name}
                    </h4>
                    <p className="text-sm text-slate-600">
                      {formatNumber(platform.followers)} followers
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-slate-800">
                    {formatNumber(platform.engagement)}
                  </p>
                  <p className="text-sm text-green-600">
                    +{platform.growth}%
                  </p>
                </div>
              </motion.div>
            ))}
          </CardContent>
        </Card>

        {/* Top Performing Posts */}
        <Card>
          <CardHeader>
            <CardTitle>Top Performing Posts</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {analyticsData.topPosts.map((post, index) => (
              <motion.div
                key={post.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
                className="p-4 bg-slate-50 rounded-lg"
              >
                <div className="flex items-start justify-between mb-2">
                  <h4 className="font-semibold text-slate-800">{post.title}</h4>
                  <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                    {post.platform}
                  </span>
                </div>
                <div className="grid grid-cols-4 gap-2 text-sm">
                  <div className="flex items-center gap-1">
                    <Eye className="w-3 h-3 text-slate-500" />
                    <span>{formatNumber(post.views)}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Heart className="w-3 h-3 text-slate-500" />
                    <span>{formatNumber(post.likes)}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Share className="w-3 h-3 text-slate-500" />
                    <span>{formatNumber(post.shares)}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <MessageCircle className="w-3 h-3 text-slate-500" />
                    <span>{formatNumber(post.comments)}</span>
                  </div>
                </div>
              </motion.div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Engagement Trends */}
      <Card>
        <CardHeader>
          <CardTitle>Engagement Trends</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span>This Week</span>
                <span>85% of goal</span>
              </div>
              <Progress value={85} className="h-2" />
            </div>
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span>This Month</span>
                <span>92% of goal</span>
              </div>
              <Progress value={92} className="h-2" />
            </div>
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span>This Quarter</span>
                <span>78% of goal</span>
              </div>
              <Progress value={78} className="h-2" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}