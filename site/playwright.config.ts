import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',timeout:90000,use:{baseURL:'http://127.0.0.1:4173'},webServer:{command:'npm run preview -- --port 4173',url:'http://127.0.0.1:4173/hardcase/',reuseExistingServer:false},reporter:'list'});
