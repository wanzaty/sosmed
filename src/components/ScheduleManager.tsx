import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Calendar, Clock, Edit, Trash2, Play, Pause } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'

interface ScheduledPost {
  id: string
  title: string
  content: string
  platforms: string[]
  scheduledTime: Date
  status: 'scheduled' | 'published' | 'failed'
  mediaCount: number
}

const mockScheduledPosts: ScheduledPost[] = [
  {
    id: '1',
    title: 'Morning Motivation',
    content: '🌅 Start your day with positive energy! Here are 3 tips to boost your morning routine...',
    platforms: ['tiktok', 'instagram', 'facebook'],
    scheduledTime: new Date(Date.now() + 2 * 60 * 60 * 1000), // 2 hours from now
    status: 'scheduled',
    mediaCount: 1
  },
  {
    id: '2',
    title: 'Product Launch',
    content: '🚀 Exciting news! Our new product is finally here. Check out what makes it special...',
    platforms: ['facebook', 'twitter', 'linkedin'],
    scheduledTime: new Date(Date.now() + 24 * 60 * 60 * 1000), // 24 hours from now
    status: 'scheduled',
    mediaCount: 3
  },
  {
    id: '3',
    title: 'Behind the Scenes',
    content: '🎬 Take a look behind the scenes of our latest project. The creative process is amazing!',
    platforms: ['youtube', 'tiktok'],
    scheduledTime: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
    status: 'published',
    mediaCount: 1
  }
]

export function ScheduleManager() {
  const [scheduledPosts, setScheduledPosts] = useState<ScheduledPost[]>(mockScheduledPosts)

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'scheduled':
        return 'bg-blue-100 text-blue-800'
      case 'published':
        return 'bg-green-100 text-green-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const formatDateTime = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date)
  }

  const deletePost = (id: string) => {
    setScheduledPosts(prev => prev.filter(post => post.id !== id))
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Schedule Manager</h2>
          <p className="text-slate-600">Manage your scheduled and published content</p>
        </div>
        <Button className="flex items-center gap-2">
          <Calendar className="w-4 h-4" />
          New Schedule
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-600">Scheduled</p>
                <p className="text-2xl font-bold text-blue-600">
                  {scheduledPosts.filter(p => p.status === 'scheduled').length}
                </p>
              </div>
              <Clock className="w-8 h-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-600">Published</p>
                <p className="text-2xl font-bold text-green-600">
                  {scheduledPosts.filter(p => p.status === 'published').length}
                </p>
              </div>
              <Play className="w-8 h-8 text-green-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-600">Failed</p>
                <p className="text-2xl font-bold text-red-600">
                  {scheduledPosts.filter(p => p.status === 'failed').length}
                </p>
              </div>
              <Pause className="w-8 h-8 text-red-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Scheduled Posts */}
      <div className="space-y-4">
        {scheduledPosts.map((post, index) => (
          <motion.div
            key={post.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: index * 0.1 }}
          >
            <Card className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-semibold text-lg">{post.title}</h3>
                      <Badge className={getStatusColor(post.status)}>
                        {post.status}
                      </Badge>
                    </div>
                    
                    <p className="text-slate-600 mb-3 line-clamp-2">
                      {post.content}
                    </p>
                    
                    <div className="flex items-center gap-4 text-sm text-slate-500">
                      <div className="flex items-center gap-1">
                        <Calendar className="w-4 h-4" />
                        {formatDateTime(post.scheduledTime)}
                      </div>
                      <div className="flex items-center gap-1">
                        <span>📎 {post.mediaCount} file{post.mediaCount > 1 ? 's' : ''}</span>
                      </div>
                    </div>
                    
                    <div className="flex flex-wrap gap-2 mt-3">
                      {post.platforms.map(platform => (
                        <Badge key={platform} variant="outline" className="capitalize">
                          {platform}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2 ml-4">
                    <Button variant="ghost" size="sm">
                      <Edit className="w-4 h-4" />
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={() => deletePost(post.id)}
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {scheduledPosts.length === 0 && (
        <Card className="text-center py-12">
          <CardContent>
            <div className="text-6xl mb-4">📅</div>
            <h3 className="text-xl font-semibold mb-2">No Scheduled Posts</h3>
            <p className="text-slate-600 mb-4">
              You don't have any scheduled posts yet. Create your first scheduled post to get started.
            </p>
            <Button>Schedule Your First Post</Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}