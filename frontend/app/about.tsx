import { View, Text } from 'react-native'
import React from 'react'
import { auth } from '@/lib/firebase'
import { Button } from '@react-navigation/elements'
import { useRouter } from 'expo-router'

type Props = {}

const AboutPage = (props: Props) => {
    const router = useRouter();
    const handleSignOut = () => {
        auth.signOut().then(() => {
            router.replace('/signin')
        })
            .catch(() => {

            })
    }
    return (
        <View>
            <Button onPressIn={handleSignOut}>Log Out</Button>
            <Text>Hello welcome to about screen.</Text>
        </View>
    )
}

export default AboutPage