/**
 * Script to copy lyrics.db to public/ directory before build
 * This ensures the database is available for the PWA
 */

import fs from 'fs/promises';
import path from 'path';

const SOURCE_DB = path.resolve('../lyrics.db');
const RELEASE_TAG = process.env.RELEASE_TAG || process.argv[2] || 'dev';
const TARGET_DB = path.resolve(`./public/lyrics.${RELEASE_TAG}.db`);

async function copyDatabase() {
  try {
    // Ensure public directory exists
    await fs.mkdir('./public', { recursive: true });
    
    // Copy the database file
    await fs.copyFile(SOURCE_DB, TARGET_DB);
    console.log(`✓ Database copied to public/lyrics.${RELEASE_TAG}.db`);
    
    // Verify the file was copied
    const stats = await fs.stat(TARGET_DB);
    console.log(`  Size: ${Math.round(stats.size / 1024 / 1024 * 100) / 100} MB`);
    
    return true;
  } catch (error) {
    console.error('✗ Failed to copy database:', error);
    return false;
  }
}

// Run and exit
copyDatabase()
  .then(success => {
    process.exit(success ? 0 : 1);
  })
  .catch(() => {
    process.exit(1);
  });
