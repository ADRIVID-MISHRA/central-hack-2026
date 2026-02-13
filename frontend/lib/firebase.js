import { initializeApp } from "firebase/app";
import {
  getAuth,
  initializeAuth,
  getReactNativePersistence,
} from "firebase/auth";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { Platform } from "react-native";

import { key } from './firebase_key'


const firebaseConfig = {
    apiKey: key.apiKey,
    authDomain: key.authDomain,
    projectId: key.projectId,
    storageBucket: key.storageBucket,
    messagingSenderId: key.messagingSenderId,
    appId: key.appId,
};

const app = initializeApp(firebaseConfig);

export const auth =
  Platform.OS === "web"
    ? getAuth(app)
    : initializeAuth(app, {
        persistence: getReactNativePersistence(AsyncStorage),
      });
