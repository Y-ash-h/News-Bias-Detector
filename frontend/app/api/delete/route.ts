import { NextResponse } from 'next/server'
import clientPromise from '@/libs/mongo'
import { Collection } from 'mongodb'

export async function DELETE() {
  try {
    const client = await clientPromise
    const collection: Collection = client.db("newsBias").collection("NewsArticles")
    
    // Find oldest 1000 documents
    const oldestDocs = await collection
      .find({})
      .sort({ published_date: 1 })
      .limit(1000)
      .toArray()
    
    const docIds = oldestDocs.map(doc => doc._id)
    
    if (docIds.length) {
      const result = await collection.deleteMany({
        _id: { $in: docIds }
      })
      
      return NextResponse.json({
        message: `Deleted ${result.deletedCount} documents`
      })
    }
    
    return NextResponse.json({
      message: "No documents to delete"
    })
  } catch (error) {
    return NextResponse.json(
      { error: `Failed to delete documents: ${error}` },
      { status: 500 }
    )
  }
}