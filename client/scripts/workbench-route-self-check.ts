import { pageFromPath, searchPageHref, workbenchPageHref } from '../src/app-page.ts';

if (pageFromPath('/workbench/', '/') !== 'workbench') throw new Error('dev route');
if (pageFromPath('/Canto-0243/workbench/', '/Canto-0243/') !== 'workbench') throw new Error('Pages route');
if (pageFromPath('/app/workbench/', '/app/') !== 'workbench') throw new Error('Portable route');
if (pageFromPath('/app/', '/app/') !== 'search') throw new Error('search route');
if (workbenchPageHref('/app/') !== '/app/workbench/') throw new Error('workbench href');
if (searchPageHref('/Canto-0243/') !== '/Canto-0243/') throw new Error('search href');

console.log('workbench route self-check ok');
