import { NextResponse } from 'next/server'
import clientPromise from '@/libs/mongo'
import { Collection } from 'mongodb'

export async function GET() {
  try {
    const client = await clientPromise
    const collection: Collection = client.db("newsBias").collection("NewsArticles")
    
    // Retrieve all documents
    const entireData = await collection
      .find({})
      .toArray()
    
    if (!entireData.length) {
      return NextResponse.json([], { status: 200 })
    }

    // Sort: items with publish date first (descending), then those without publish date at the end
    const sortedData = entireData.sort((a, b) => {
      const aHasDate = !!a.published;
      const bHasDate = !!b.published;
      if (aHasDate && bHasDate) {
        // If both have published date, sort descending
        return new Date(b.published).getTime() - new Date(a.published).getTime();
      }
      if (aHasDate) return -1; // a comes before b
      if (bHasDate) return 1;  // b comes before a
      return 0; // both have no published date
    });

    return NextResponse.json(sortedData)
  } catch (error) {
    // Surface the actual error in server logs and response for debugging
    console.error("/api/cache GET failed:", error)
    const message = error instanceof Error ? `${error.name}: ${error.message}` : String(error)
    const stack = error instanceof Error ? error.stack : undefined
    return NextResponse.json(
      { error: "Failed to retrieve cached data", message, stack },
      { status: 500 }
    )
  }
}
