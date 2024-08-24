//
//  Cross_PlatformApp.swift
//  Cross Platform
//
//  Created by Armaan Nakhuda on 27/07/24.
//

//import SwiftUI
//import SwiftData
//
//@main
//struct Cross_PlatformApp: App {
//    var sharedModelContainer: ModelContainer = {
//        let schema = Schema([
//            Item.self,
//        ])
//        let modelConfiguration = ModelConfiguration(schema: schema, isStoredInMemoryOnly: false)
//
//        do {
//            return try ModelContainer(for: schema, configurations: [modelConfiguration])
//        } catch {
//            fatalError("Could not create ModelContainer: \(error)")
//        }
//    }()
//
//    var body: some Scene {
//        WindowGroup {
//            ContentView()
//        }
//        .modelContainer(sharedModelContainer)
//    }
//}

import SwiftUI

@main
struct Cross_PlatformApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(SendingDiscovery())
                .environmentObject(ReceiverNetwork())
                
        }
    }
}


