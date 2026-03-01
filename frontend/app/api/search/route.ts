import { NextResponse } from 'next/server'
import clientPromise from '@/libs/mongo'
import { Collection } from 'mongodb'

export async function POST(request: Request) {
  try {
    const { keyword } = await request.json()
    
    if (!keyword) {
      return NextResponse.json(
        { error: "No keyword provided" },
        { status: 400 }
      )
    }

    const client = await clientPromise
    const collection: Collection = client.db("newsBias").collection("NewsArticles")
    
    // Create text index
    await collection.createIndex({ title: "text", text: "text" })
    
    // Perform text search
    const articles = await collection
      .find(
        { $text: { $search: keyword } },
        { projection: { score: { $meta: "textScore" } } }
      )
      .sort({ score: { $meta: "textScore" } })
      .toArray()
    
    if (!articles.length) {
      return NextResponse.json(
        { message: "No articles found" },
        { status: 404 }
      )
    }
    
    return NextResponse.json(articles)
  } catch (error) {
    return NextResponse.json(
      { error: `Search failed: ${error}` },
      { status: 500 }
    )
  }
}