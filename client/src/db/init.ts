/**
 * Database Initialization with sql.js and httpvfs
 * Handles loading lyrics.db as a static asset with chunked/streamed loading
 */

import initSqlJs, { Database } from 'sql.js';
import { createHttpVfs, HttpDatabase } from 'sql.js-httpvfs';

// Database instance singleton
let db: Database | null = null;
let isInitialized = false;

/**
 * Initialize the SQL.js database with lyrics.db
 * Uses httpvfs for efficient chunked loading of large database files
 */
export async function initializeDatabase(dbPath: string = '/lyrics.db'): Promise<Database> {
  if (db && isInitialized) {
    return db;
  }

  try {
    // Initialize SQL.js
    const SQL = await initSqlJs({
      locateFile: (file: string) => {
        // For wasm file, use the imported version
        if (file.endsWith('.wasm')) {
          return `https://sql.js.org/dist/${file}`;
        }
        return file;
      }
    });

    // Create HTTPVFS for chunked loading
    const vfs = createHttpVfs(dbPath, {
      fetch: window.fetch.bind(window),
      onprogress: (loaded: number, total: number) => {
        console.log(`Loading database: ${Math.round((loaded / total) * 100)}%`);
      }
    });

    // Open database with HTTPVFS
    db = new SQL.Database('/lyrics.db', { vfs });
    
    // Mark as initialized
    isInitialized = true;
    
    console.log('Database initialized successfully with httpvfs');
    return db;

  } catch (error) {
    console.error('Failed to initialize database with httpvfs, falling back to fetch + import:', error);
    
    // Fallback: Try direct fetch and import
    try {
      const SQL = await initSqlJs({
        locateFile: (file: string) => {
          if (file.endsWith('.wasm')) {
            return `https://sql.js.org/dist/${file}`;
          }
          return file;
        }
      });
      
      const response = await fetch(dbPath);
      const arrayBuffer = await response.arrayBuffer();
      const uint8Array = new Uint8Array(arrayBuffer);
      
      db = new SQL.Database(uint8Array);
      isInitialized = true;
      console.log('Database initialized successfully with direct import');
      return db;
    } catch (fallbackError) {
      console.error('Failed to initialize database:', fallbackError);
      throw new Error('Could not initialize database. Please ensure lyrics.db is accessible.');
    }
  }
}

/**
 * Get the database instance
 * Throws if database is not initialized
 */
export function getDatabase(): Database {
  if (!db) {
    throw new Error('Database not initialized. Call initializeDatabase() first.');
  }
  return db;
}

/**
 * Check if database is initialized
 */
export function isDatabaseInitialized(): boolean {
  return isInitialized;
}

/**
 * Reset database instance (useful for testing)
 */
export function resetDatabase(): void {
  if (db) {
    db.close();
    db = null;
    isInitialized = false;
  }
}

// Export the database instance for direct use (after initialization)
export { db };
