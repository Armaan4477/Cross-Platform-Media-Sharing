//
//  Item.swift
//  Cross Platform
//
//  Created by Armaan Nakhuda on 27/07/24.
//

//import Foundation
//import SwiftData
//
//@Model
//final class Item {
//    var timestamp: Date
//    
//    init(timestamp: Date) {
//        self.timestamp = timestamp
//    }
//}

import Foundation
import CoreData

@objc(Item)
public class Item: NSManagedObject, Identifiable {
    @NSManaged public var id: UUID?
    @NSManaged public var name: String?
}

extension Item {
    static func getAllItems() -> NSFetchRequest<Item> {
        let request: NSFetchRequest<Item> = Item.fetchRequest() as! NSFetchRequest<Item>
        request.sortDescriptors = [NSSortDescriptor(key: "name", ascending: true)]
        return request
    }
}
